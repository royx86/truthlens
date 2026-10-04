"""Unified Analysis Orchestration Service for TruthLens.

Coordinates the end-to-end pipeline:
Platform Detection → Scraping → Media/Vision Analysis → Content Normalization →
Claim Extraction → Claim Filtering → Evidence Search → Evidence Ranking →
Fact-Check Reasoning → Normalized Final Report.

This is the ONLY place that chains pipeline stages.
All internal communication is via direct Python service calls — NO internal HTTP requests.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from app.core.timing import (
    StageTracker,
    generate_job_id,
    set_current_job_id,
    set_current_tracker,
    timed_stage,
)
from app.platforms.detector import detect_platform
from app.schemas.analysis import (
    AnalysisInput,
    AnalyzedMedia,
    ClaimExtractionResult,
    SourceInfo,
)
from app.schemas.post import Author
from app.schemas.report import (
    FactCheckAnalysis,
    UnifiedAnalysisData,
    UnifiedAnalysisResponse,
)
from app.services.claim_extraction_service import ClaimExtractionService
from app.services.content_analysis import ContentAnalysisService
from app.services.evidence_ranking_service import EvidenceRankingService
from app.services.evidence_search_service import EvidenceSearchService
from app.services.reasoning_service import ReasoningService
from app.services.scraper_service import scrape_social_post

logger = logging.getLogger(__name__)


def _normalize_media_for_response(media: List[AnalyzedMedia]) -> List[Dict[str, Any]]:
    """Serialize AnalyzedMedia to the canonical response format.

    Single source of truth for extracted_text: analysis.extracted_text
    No duplicate ocr_text, no combined_ocr_text.
    """
    result = []
    for m in media:
        item: Dict[str, Any] = {
            "type": m.type,
            "url": m.url,
            "thumbnail_url": m.thumbnail_url,
        }
        analysis_status = getattr(m, "analysis_status", "success")
        item["analysis_status"] = analysis_status
        if m.visual_analysis is not None:
            va = m.visual_analysis
            item["analysis"] = {
                "analysis_status": analysis_status,
                # canonical extracted text: single location
                "extracted_text": va.extracted_text or m.extracted_text or "",
                "description": va.description,
                "has_visible_text": va.has_visible_text,
                "visible_elements": va.observed_visual_details,
                "people": [p.model_dump() for p in va.people],
                "objects": va.objects,
                "manipulation_signals": va.potential_manipulation_signals,
                "uncertainty": va.uncertainty,
            }
        else:
            # No visual analysis: use extracted_text from OCR fallback
            item["analysis"] = {
                "analysis_status": analysis_status,
                "extracted_text": m.extracted_text or "",
                "description": None,
                "has_visible_text": bool(m.extracted_text),
                "visible_elements": [],
                "people": [],
                "objects": [],
                "manipulation_signals": [],
                "uncertainty": [],
            }

        if m.analysis_error:
            item["analysis_error"] = m.analysis_error
            item["analysis"]["analysis_error"] = m.analysis_error
        if getattr(m, "analysis_error_type", None):
            item["analysis_error_type"] = m.analysis_error_type
            item["analysis"]["analysis_error_type"] = m.analysis_error_type

        result.append(item)
    return result


class AnalysisService:
    """Central orchestrator coordinating the modular analysis pipeline.

    Architecture:
      AnalysisService
        ├── ContentAnalysisService  (vision/OCR on media)
        ├── ClaimExtractionService  (LLM claim identification + classification)
        ├── EvidenceSearchService   (web search per claim)
        ├── EvidenceRankingService  (source quality/relevance ranking)
        └── ReasoningService        (LLM fact-check verdict per claim)
    """

    def __init__(
        self,
        content_analysis_service: Optional[ContentAnalysisService] = None,
        claim_extraction_service: Optional[ClaimExtractionService] = None,
        evidence_search_service: Optional[EvidenceSearchService] = None,
        evidence_ranking_service: Optional[EvidenceRankingService] = None,
        reasoning_service: Optional[ReasoningService] = None,
    ):
        self.content_analysis_service = content_analysis_service or ContentAnalysisService()
        self.claim_extraction_service = claim_extraction_service or ClaimExtractionService()
        self.evidence_ranking_service = evidence_ranking_service or EvidenceRankingService()
        self.reasoning_service = reasoning_service or ReasoningService()
        # evidence_search_service initialized per-request with the original post URL
        self._evidence_search_service_override = evidence_search_service

    async def analyze_url(
        self,
        url: str,
        job_id: Optional[str] = None,
    ) -> UnifiedAnalysisResponse:
        """Run the complete end-to-end analysis pipeline for a social media URL."""
        jid = job_id or generate_job_id()
        set_current_job_id(jid)
        tracker = StageTracker(job_id=jid)
        set_current_tracker(tracker)

        clean_url = url.strip()
        start_total = time.perf_counter()

        logger.info(f"[PIPELINE] START job_id={jid} url={clean_url!r}")

        try:
            # ── Stage 1: Platform Detection ───────────────────────────────
            platform = detect_platform(clean_url)
            logger.info(f"[PLATFORM] platform={platform} job_id={jid}")

            # ── Stage 2: Scraping ─────────────────────────────────────────
            async with timed_stage("SCRAPING", job_id=jid, tracker=tracker):
                post = await scrape_social_post(clean_url)

            logger.info(
                f"[SCRAPE] platform={post.platform} media_count={len(post.media)} job_id={jid}"
            )

            # ── Stage 3: Media & Vision Analysis ─────────────────────────
            t_media = time.perf_counter()
            try:
                async with timed_stage("MEDIA_ANALYSIS", job_id=jid, tracker=tracker):
                    analysis_input = await self.content_analysis_service.analyze(post)
                media_duration = time.perf_counter() - t_media
                logger.info(
                    f"[MEDIA_ANALYSIS] images_analyzed={len(analysis_input.media)} "
                    f"duration={media_duration:.2f}s job_id={jid}"
                )
            except Exception as exc:
                media_duration = time.perf_counter() - t_media
                logger.warning(
                    f"[MEDIA_ANALYSIS] partial_failure={exc} duration={media_duration:.2f}s "
                    f"job_id={jid}",
                    exc_info=True,
                )
                analysis_input = AnalysisInput(
                    source=SourceInfo(platform=post.platform, url=post.url),
                    author=post.author,
                    post_text=post.text,
                    media=[],
                    extracted_text=None,
                )

            # ── Stage 4: Claim Extraction ────────────────────────────────
            context_flags = ["none"]
            t_claims = time.perf_counter()
            try:
                async with timed_stage("CLAIM_EXTRACTION", job_id=jid, tracker=tracker):
                    claims_result = await self.claim_extraction_service.extract_claims(
                        analysis_input
                    )
                    context_flags = claims_result.context_flags
                    analysis_input.claims = claims_result
                claims_duration = time.perf_counter() - t_claims
                factual_count = sum(
                    1 for c in claims_result.items if c.claim_type == "factual"
                )
                logger.info(
                    f"[CLAIM_EXTRACTION] total={len(claims_result.items)} "
                    f"factual={factual_count} "
                    f"context_flags={context_flags} "
                    f"duration={claims_duration:.2f}s job_id={jid}"
                )
            except Exception as exc:
                claims_duration = time.perf_counter() - t_claims
                logger.error(
                    f"[CLAIM_EXTRACTION] error={exc} duration={claims_duration:.2f}s job_id={jid}",
                    exc_info=True,
                )
                claims_result = ClaimExtractionResult(
                    context_flags=["none"],
                    items=[],
                    error=f"Claim extraction failed: {str(exc)}",
                )
                analysis_input.claims = claims_result

            claims = claims_result.items or []

            # ── Stage 5: Evidence Search ─────────────────────────────────
            # Initialize EvidenceSearchService with the original post URL so
            # results from that URL are tagged as source_role="original_post"
            evidence_search_service = self._evidence_search_service_override or EvidenceSearchService(
                original_post_url=clean_url
            )

            t_search = time.perf_counter()
            try:
                async with timed_stage("EVIDENCE_SEARCH", job_id=jid, tracker=tracker):
                    claim_evidence_list = await evidence_search_service.search_for_claims(claims)
                search_duration = time.perf_counter() - t_search
                total_evidence = sum(len(ce.evidence) for ce in claim_evidence_list)
                logger.info(
                    f"[EVIDENCE_SEARCH] claims_searched={len(claims)} "
                    f"total_evidence={total_evidence} "
                    f"duration={search_duration:.2f}s job_id={jid}"
                )
            except Exception as exc:
                search_duration = time.perf_counter() - t_search
                logger.error(
                    f"[EVIDENCE_SEARCH] error={exc} duration={search_duration:.2f}s job_id={jid}",
                    exc_info=True,
                )
                claim_evidence_list = []

            # ── Stage 6: Evidence Ranking ────────────────────────────────
            t_rank = time.perf_counter()
            try:
                async with timed_stage("EVIDENCE_RANKING", job_id=jid, tracker=tracker):
                    ranked_evidence_list = self.evidence_ranking_service.rank_claims_evidence(
                        claim_evidence_list
                    )
                rank_duration = time.perf_counter() - t_rank
                logger.info(
                    f"[EVIDENCE_RANKING] claims_ranked={len(ranked_evidence_list)} "
                    f"duration={rank_duration:.2f}s job_id={jid}"
                )
            except Exception as exc:
                rank_duration = time.perf_counter() - t_rank
                logger.error(
                    f"[EVIDENCE_RANKING] error={exc} duration={rank_duration:.2f}s job_id={jid}",
                    exc_info=True,
                )
                ranked_evidence_list = []

            # ── Stage 7: Fact-Check Reasoning ────────────────────────────
            # Only pass media description context (not repeated post text)
            media_desc_parts = [
                m.visual_analysis.description
                for m in analysis_input.media
                if m.visual_analysis and m.visual_analysis.description
            ]
            media_context_str = " | ".join(media_desc_parts) if media_desc_parts else None

            t_reasoning = time.perf_counter()
            try:
                async with timed_stage("REASONING", job_id=jid, tracker=tracker):
                    fact_check_analysis = await self.reasoning_service.evaluate_claims(
                        claims=claims,
                        evidence_by_claim=ranked_evidence_list,
                        context_flags=context_flags,
                        post_context=analysis_input.post_text,
                        media_context=media_context_str,
                    )
                reasoning_duration = time.perf_counter() - t_reasoning
                failed_claims = sum(
                    1 for a in fact_check_analysis.claims if a.verdict is None
                )
                logger.info(
                    f"[REASONING] claims_assessed={fact_check_analysis.claims_analyzed} "
                    f"failed={failed_claims} "
                    f"duration={reasoning_duration:.2f}s job_id={jid}"
                )
            except Exception as exc:
                reasoning_duration = time.perf_counter() - t_reasoning
                logger.error(
                    f"[REASONING] error={exc} duration={reasoning_duration:.2f}s job_id={jid}",
                    exc_info=True,
                )
                fact_check_analysis = FactCheckAnalysis(
                    claims=[],
                    overall_summary=f"Fact-checking reasoning could not complete: {str(exc)}",
                    context_flags=context_flags,
                    claims_analyzed=0,
                )

            # ── Stage 8: Build Normalized Final Report ───────────────────
            with timed_stage("REPORT", job_id=jid, tracker=tracker):
                normalized_media = _normalize_media_for_response(analysis_input.media)

                unified_data = UnifiedAnalysisData(
                    source=analysis_input.source,
                    author=analysis_input.author,
                    content={
                        # Single canonical source of truth — zero duplication
                        "text": analysis_input.post_text,
                        "media": normalized_media,
                    },
                    context={"flags": context_flags},
                    claims=claims,
                    evidence=ranked_evidence_list,
                    analysis=fact_check_analysis,
                )

            total_duration = time.perf_counter() - start_total
            evidence_count = sum(len(ce.sources) for ce in ranked_evidence_list)
            logger.info(
                f"[PIPELINE] END job_id={jid} claims={len(claims)} "
                f"evidence={evidence_count} "
                f"total_duration={total_duration:.2f}s"
            )

            return UnifiedAnalysisResponse(
                status="success",
                data=unified_data,
            )

        finally:
            tracker.log_summary()
