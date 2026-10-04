"""
Pydantic schemas for the Content Analysis (OCR + Vision) phase.

Separation of concerns:
- post_text: Original social media post caption/text
- extracted_text: Text physically visible inside images (canonical field)
- visual_analysis: What the image visually depicts (analyzed by Groq Vision)
"""

from typing import Any, Literal, Optional
from pydantic import BaseModel, Field

from app.schemas.post import Author


class PersonAnalysis(BaseModel):
    description: str
    identity: str | None = None
    identity_confidence: Literal[
        "certain_from_context",
        "probable",
        "uncertain",
        "unknown",
    ] | None = None
    identity_basis: str | None = None


class VisualAnalysis(BaseModel):
    description: str
    extracted_text: str | None = None
    has_visible_text: bool | None = None
    people: list[PersonAnalysis] = Field(default_factory=list)
    objects: list[str] = Field(default_factory=list)
    scene: str | None = None
    actions: list[str] = Field(default_factory=list)
    visible_text: list[str] = Field(default_factory=list)
    observed_visual_details: list[str] = Field(default_factory=list)
    potential_manipulation_signals: list[str] = Field(default_factory=list)
    uncertainty: list[str] = Field(default_factory=list)


class SourceInfo(BaseModel):
    platform: str
    url: str


class AnalyzedMedia(BaseModel):
    """A single media item with its normalized vision analysis result.

    Canonical extracted text is in analysis.extracted_text (via visual_analysis).
    The top-level extracted_text is kept for direct access convenience;
    ocr_text is removed to avoid duplication.
    """

    type: str
    url: str | None = None
    thumbnail_url: str | None = None
    analysis_status: Literal["success", "partial", "failed", "skipped"] = "success"
    # Canonical extracted text from vision/OCR — single source of truth
    extracted_text: str | None = None
    # visual_analysis.extracted_text is the same value; no separate ocr_text field
    visual_analysis: VisualAnalysis | None = None
    analysis_error: str | None = None
    analysis_error_type: Optional[Literal["rate_limited", "api_error", "timeout", "parse_error"]] = None


class Claim(BaseModel):
    claim_id: str
    text: str
    priority: Literal["primary", "secondary", "narrative"] = "primary"
    importance: Literal["high", "medium", "low"] = "medium"
    source: Literal["post_text", "image_text", "video_transcript", "mixed"] = "mixed"
    requires_verification: bool = True
    # claim_type helps the pipeline categorize claims and handle absence of evidence
    claim_type: Literal["factual", "narrative", "opinion", "satire", "absence_of_evidence"] = "factual"
    primary_query: Optional[str] = None
    fallback_queries: list[str] = Field(default_factory=list)
    search_query: Optional[str] = None


class ClaimExtractionResult(BaseModel):
    context_flags: list[Literal["satire", "parody", "fictional", "hypothetical", "opinion", "none"]] = Field(
        default_factory=lambda: ["none"]
    )
    items: list[Claim] = Field(default_factory=list)
    error: str | None = None


class AnalysisInput(BaseModel):
    source: SourceInfo
    author: Author | None = None
    post_text: str | None = None
    media: list[AnalyzedMedia] = Field(default_factory=list)
    # Canonical combined extracted text from all images — single source of truth
    extracted_text: str | None = None
    claims: ClaimExtractionResult | None = None


# ── API Envelopes ────────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    url: str


class AnalysisResponse(BaseModel):
    status: str = "success"
    data: AnalysisInput
