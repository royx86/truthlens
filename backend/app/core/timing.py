"""Performance timing and structured logging helpers for TruthLens pipeline."""

from __future__ import annotations

import contextvars
from datetime import datetime
import logging
import time
from typing import Any, Dict, Optional
import uuid

# Context variables to hold active job ID and stage tracker across async/sync calls
_current_job_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("current_job_id", default=None)
_current_tracker: contextvars.ContextVar[Optional["StageTracker"]] = contextvars.ContextVar("current_tracker", default=None)

logger = logging.getLogger("truthlens.timing")


class TruthLensFormatter(logging.Formatter):
    """Custom logging formatter that produces clean millisecond timestamps:
    YYYY-MM-DD HH:MM:SS.mmm | LEVEL | message
    """

    def formatTime(self, record: logging.LogRecord, datefmt: Optional[str] = None) -> str:
        ct = datetime.fromtimestamp(record.created)
        return ct.strftime("%Y-%m-%d %H:%M:%S") + f".{int(record.msecs):03d}"

    def format(self, record: logging.LogRecord) -> str:
        record.asctime = self.formatTime(record)
        # Pad levelname to 5 chars (INFO , ERROR, WARN , DEBUG)
        level_padded = f"{record.levelname:<5}"
        return f"{record.asctime} | {level_padded} | {record.getMessage()}"


def setup_logging(level: int = logging.INFO) -> None:
    """Configures the root and truthlens loggers with TruthLensFormatter."""
    root = logging.getLogger()
    
    # Avoid duplicate handlers if setup_logging is called multiple times
    has_custom_handler = any(isinstance(h.formatter, TruthLensFormatter) for h in root.handlers)
    if not has_custom_handler:
        handler = logging.StreamHandler()
        handler.setFormatter(TruthLensFormatter())
        root.handlers.clear()
        root.addHandler(handler)
        root.setLevel(level)


def generate_job_id() -> str:
    """Generate a clean 12-character hex job identifier."""
    return uuid.uuid4().hex[:12]


def get_current_job_id() -> Optional[str]:
    """Retrieve the currently bound job_id from context."""
    return _current_job_id.get()


def set_current_job_id(job_id: Optional[str]) -> contextvars.Token:
    """Bind job_id to the current context."""
    return _current_job_id.set(job_id)


def get_current_tracker() -> Optional["StageTracker"]:
    """Retrieve the currently bound StageTracker from context."""
    return _current_tracker.get()


def set_current_tracker(tracker: Optional["StageTracker"]) -> contextvars.Token:
    """Bind StageTracker to the current context."""
    return _current_tracker.set(tracker)


class StageTracker:
    """Tracks stage start/end times and formats pipeline summary logs."""

    def __init__(self, job_id: str):
        self.job_id = job_id
        self.start_time = time.perf_counter()
        self.stage_durations: Dict[str, float] = {}

    def record_stage(self, stage: str, duration: float) -> None:
        """Record stage execution duration in seconds.
        Normalizes stage name to lowercase snake_case for summary output.
        """
        stage_key = stage.lower().replace(" ", "_")
        # If the same stage runs multiple times (e.g. per-image OCR), accumulate duration
        self.stage_durations[stage_key] = self.stage_durations.get(stage_key, 0.0) + duration

    def get_total_duration(self) -> float:
        return time.perf_counter() - self.start_time

    def get_summary_log(self) -> str:
        """Format the end-of-pipeline summary string.
        Example: [TRUTHLENS] [job_id=abc123] [SUMMARY] total_duration=10.15s scrape_duration=8.42s image_analysis_duration=1.73s
        """
        total = self.get_total_duration()
        summary_parts = [
            f"[TRUTHLENS] [job_id={self.job_id}] [SUMMARY]",
            f"total_duration={total:.2f}s",
        ]
        for stage_key, dur in self.stage_durations.items():
            summary_parts.append(f"{stage_key}_duration={dur:.2f}s")
        return " ".join(summary_parts)

    def log_summary(self, log_level: int = logging.INFO) -> None:
        """Emit the formatted summary log."""
        logger.log(log_level, self.get_summary_log())


def format_metadata(metadata: Optional[Dict[str, Any]]) -> str:
    """Format non-sensitive metadata dictionary into key=val pairs."""
    if not metadata:
        return ""
    parts = []
    for k, v in metadata.items():
        if v is not None:
            v_str = str(v)
            if isinstance(v, str) and (k == "reason" or " " in v_str) and not (v_str.startswith('"') and v_str.endswith('"')):
                parts.append(f'{k}="{v_str}"')
            else:
                parts.append(f"{k}={v_str}")
    return " ".join(parts)


def log_stage_event(
    stage: str,
    message: str,
    job_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    log_level: int = logging.INFO,
) -> None:
    """Log an ad-hoc point-in-time event for a stage.
    Example: [TRUTHLENS] [job_id=abc123] [OCR] SKIPPED reason="vision_extracted_text_available"
    """
    jid = job_id or get_current_job_id() or "unknown"
    meta_str = format_metadata(metadata)
    meta_part = f" {meta_str}" if meta_str else ""
    msg_part = f" {message}" if message else ""
    logger.log(log_level, f"[TRUTHLENS] [job_id={jid}] [{stage.upper()}]{msg_part}{meta_part}")


class timed_stage:
    """Context manager for timing pipeline stages, supporting both sync and async blocks.

    Usage:
        with timed_stage("SCRAPE", metadata={"platform": "instagram"}):
            ...

        async with timed_stage("OCR", is_fallback=True, metadata={"reason": "vision_extracted_text_empty"}):
            ...
    """

    def __init__(
        self,
        stage: str,
        job_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tracker: Optional[StageTracker] = None,
        log_start: bool = True,
        is_fallback: bool = False,
    ):
        self.stage = stage.upper()
        self.job_id = job_id or get_current_job_id() or "unknown"
        self.metadata = metadata or {}
        self.tracker = tracker or get_current_tracker()
        self.log_start = log_start
        self.is_fallback = is_fallback
        self.start_perf: float = 0.0
        self.duration: float = 0.0

    def _on_enter(self) -> "timed_stage":
        self.start_perf = time.perf_counter()
        if self.log_start:
            meta_str = format_metadata(self.metadata)
            meta_part = f" {meta_str}" if meta_str else ""
            prefix = "FALLBACK " if self.is_fallback else ""
            logger.info(f"[TRUTHLENS] [job_id={self.job_id}] [{self.stage}] {prefix}START{meta_part}")
        return self

    def _on_exit(self, exc_type: Optional[type], exc_val: Optional[BaseException]) -> None:
        self.duration = time.perf_counter() - self.start_perf
        if self.tracker:
            self.tracker.record_stage(self.stage, self.duration)

        meta_str = format_metadata(self.metadata)
        prefix = "FALLBACK " if self.is_fallback else ""

        if exc_type is not None:
            err_msg = str(exc_val).replace("\n", " ")
            if len(err_msg) > 120:
                err_msg = err_msg[:117] + "..."
            logger.error(
                f"[TRUTHLENS] [job_id={self.job_id}] [{self.stage}] {prefix}ERROR duration={self.duration:.2f}s error={err_msg!r}"
            )
        else:
            end_meta = ""
            if not self.is_fallback and meta_str:
                end_meta = f" {meta_str}"
            logger.info(
                f"[TRUTHLENS] [job_id={self.job_id}] [{self.stage}] {prefix}END duration={self.duration:.2f}s{end_meta}"
            )

    def __enter__(self) -> "timed_stage":
        return self._on_enter()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self._on_exit(exc_type, exc_val)

    async def __aenter__(self) -> "timed_stage":
        return self._on_enter()

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        self._on_exit(exc_type, exc_val)
