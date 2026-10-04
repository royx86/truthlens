"""
Content Analysis Service.

Orchestrates Vision Analysis and OCR on NormalizedPost objects.

Pipeline:
    NormalizedPost
          │
          ├── post.text → AnalysisInput.post_text
          │
          └── media[]
                 │
                 ├── Vision AI (Groq qwen/qwen3.8-27b) → extracted_text, description, visual details
                 │
                 └── [Fallback only] OCR (Tesseract) if vision text extraction is empty/insufficient
                        │
                        ▼
                  AnalysisInput
"""

import logging
from typing import Sequence

from app.core.timing import log_stage_event, timed_stage
from app.schemas.analysis import (
    AnalysisInput,
    AnalyzedMedia,
    SourceInfo,
    VisualAnalysis,
)
from app.schemas.post import Media, NormalizedPost
from app.services.ocr_service import OCRService
from app.services.vision_service import VisionService

logger = logging.getLogger(__name__)


class ContentAnalysisService:
    def __init__(
        self,
        ocr_service: OCRService | None = None,
        vision_service: VisionService | None = None,
    ) -> None:
        self.ocr_service = ocr_service or OCRService()
        self.vision_service = vision_service or VisionService()

    async def analyze(self, post: NormalizedPost) -> AnalysisInput:
        """
        Analyze a NormalizedPost:
        1. Preserves post.text
        2. Runs Vision analysis (and OCR fallback if needed) on images
        3. Marks videos/unsupported media cleanly without crashing
        4. Combines canonical extracted text across all images
        """
        analyzed_media_list: list[AnalyzedMedia] = []
        extracted_texts: list[str] = []

        image_count = sum(1 for m in post.media if m.type == "image")
        log_stage_event("IMAGE_ANALYSIS", f"image_count={image_count}")

        for index, item in enumerate(post.media, start=1):
            async with timed_stage("IMAGE_ANALYSIS", metadata={"image": index}):
                analyzed_item = await self._process_media_item(item, index=index)
                analyzed_media_list.append(analyzed_item)
                if analyzed_item.extracted_text and analyzed_item.extracted_text.strip():
                    extracted_texts.append(analyzed_item.extracted_text.strip())

        combined_extracted_text = self._combine_ocr_texts(extracted_texts)

        return AnalysisInput(
            source=SourceInfo(
                platform=post.platform,
                url=post.url,
            ),
            author=post.author,
            post_text=post.text,
            media=analyzed_media_list,
            # canonical combined extracted text from all images — single source of truth
            extracted_text=combined_extracted_text,
        )

    async def _process_media_item(self, item: Media, index: int) -> AnalyzedMedia:
        """Process a single media item according to its type."""
        # Video: Not yet implemented, return clear error message without crashing
        if item.type == "video":
            return AnalyzedMedia(
                type="video",
                url=item.url,
                thumbnail_url=item.thumbnail_url,
                analysis_status="skipped",
                extracted_text=None,
                visual_analysis=None,
                analysis_error="Video analysis not implemented yet",
            )

        # Non-image types (audio, unknown)
        if item.type != "image":
            return AnalyzedMedia(
                type=item.type,
                url=item.url,
                thumbnail_url=item.thumbnail_url,
                analysis_status="skipped",
                extracted_text=None,
                visual_analysis=None,
                analysis_error=f"{item.type.capitalize()} analysis not implemented yet",
            )

        # Image processing: Vision First → OCR Fallback if needed
        image_url = item.url or item.thumbnail_url
        if not image_url:
            return AnalyzedMedia(
                type="image",
                url=None,
                thumbnail_url=item.thumbnail_url,
                analysis_status="failed",
                extracted_text="",
                visual_analysis=None,
                analysis_error="Image URL not provided in media",
                analysis_error_type="api_error",
            )

        # 1. Primary: Vision Analysis (Groq qwen/qwen3.8-27b)
        visual_analysis: VisualAnalysis | None = None
        vision_error: str | None = None
        try:
            async with timed_stage("VISION_ANALYSIS", metadata={"image": index}):
                vision_result = await self.vision_service.analyze_image_url(image_url)
                visual_analysis = vision_result.analysis
                if not vision_result.success:
                    vision_error = vision_result.error
        except Exception as exc:
            logger.warning("Unexpected exception during vision analysis for image %d: %s", index, exc)
            vision_error = f"Vision analysis failed: {exc}"

        # 2. Inspect extracted text from Vision AI
        vision_text: str = ""
        if visual_analysis is not None:
            if visual_analysis.extracted_text and visual_analysis.extracted_text.strip():
                vision_text = visual_analysis.extracted_text.strip()
            elif visual_analysis.visible_text:
                vision_text = "\n".join(t for t in visual_analysis.visible_text if t.strip()).strip()

        extracted_text: str = ""
        ocr_error: str | None = None

        if vision_text:
            # Vision AI extracted text successfully -> Skip OCR
            log_stage_event("OCR", 'SKIPPED reason="vision_extracted_text_available"')
            extracted_text = vision_text
        elif visual_analysis is not None and visual_analysis.has_visible_text is False:
            # Vision AI determined image contains no visible text -> Skip OCR
            log_stage_event("OCR", 'SKIPPED reason="no_visible_text"')
            extracted_text = ""
        else:
            # Fallback to dedicated OCR (Tesseract)
            fallback_reason = "vision_failed" if visual_analysis is None else "vision_extracted_text_empty"
            try:
                async with timed_stage("OCR", is_fallback=True, metadata={"reason": fallback_reason}):
                    ocr_result = await self.ocr_service.extract_text_from_url(image_url)
                    if ocr_result.success and ocr_result.text and ocr_result.text.strip():
                        extracted_text = ocr_result.text.strip()
                    elif not ocr_result.success:
                        ocr_error = ocr_result.error
            except Exception as exc:
                logger.warning("Unexpected exception during OCR fallback for image %d: %s", index, exc)
                ocr_error = f"OCR fallback failed: {exc}"

        # If neither produced text but scraper already had OCR metadata (e.g. Facebook ocrText)
        if not extracted_text and item.ocr_text:
            extracted_text = item.ocr_text

        # Synchronize visual_analysis if fallback OCR produced text
        if visual_analysis is not None and extracted_text:
            if not visual_analysis.extracted_text:
                visual_analysis.extracted_text = extracted_text
            if not visual_analysis.visible_text:
                visual_analysis.visible_text = [line.strip() for line in extracted_text.splitlines() if line.strip()]

        # Combine analysis errors if any
        analysis_error: str | None = None
        analysis_error_type: Optional[Literal["rate_limited", "api_error", "timeout", "parse_error"]] = None

        if vision_error:
            v_err_lower = vision_error.lower()
            if "429" in v_err_lower or ("rate" in v_err_lower and "limit" in v_err_lower):
                analysis_error_type = "rate_limited"
            elif "timeout" in v_err_lower or "timed out" in v_err_lower:
                analysis_error_type = "timeout"
            else:
                analysis_error_type = "api_error"

        if visual_analysis is None:
            if ocr_error:
                analysis_error = f"Vision: {vision_error}; OCR fallback: {ocr_error}"
            else:
                analysis_error = vision_error

        # Determine explicit analysis status: success, partial, failed, skipped
        has_useful_data = bool(extracted_text and extracted_text.strip()) or (
            visual_analysis is not None and bool(visual_analysis.description or visual_analysis.objects)
        )
        has_error = bool(vision_error or (visual_analysis is None and ocr_error))

        if not has_error and visual_analysis is not None:
            analysis_status: Literal["success", "partial", "failed", "skipped"] = "success"
        elif has_error and has_useful_data:
            analysis_status = "partial"
        elif has_error and not has_useful_data:
            analysis_status = "failed"
        else:
            analysis_status = "success"

        logger.info(
            f"[TRUTHLENS] [VISION_ANALYSIS] image_index={index} analysis_status={analysis_status} "
            f"has_extracted_text={bool(extracted_text)} error_type={analysis_error_type or 'none'}"
        )

        return AnalyzedMedia(
            type="image",
            url=item.url,
            thumbnail_url=item.thumbnail_url,
            analysis_status=analysis_status,
            # extracted_text is canonical; visual_analysis.extracted_text mirrors it
            extracted_text=extracted_text,
            visual_analysis=visual_analysis,
            analysis_error=analysis_error,
            analysis_error_type=analysis_error_type,
        )

    @staticmethod
    def _combine_ocr_texts(texts: Sequence[str]) -> str:
        """
        Combine non-empty OCR texts across images.
        If no text is detected: returns ""
        If single image with text: returns the text
        If multiple images with text: formatted with [Image N] headers
        """
        if not texts:
            return ""

        if len(texts) == 1:
            return texts[0]

        parts: list[str] = []
        for i, text in enumerate(texts, start=1):
            parts.append(f"[Image {i}]\n{text}")

        return "\n\n".join(parts)
