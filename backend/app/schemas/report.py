"""Pydantic schemas for Evidence Ranking, Fact-Check Reasoning, and the Unified Analysis Report."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field

from app.schemas.analysis import (
    AnalyzedMedia,
    Claim,
    SourceInfo,
)
from app.schemas.evidence import Evidence, SearchAttempt
from app.schemas.post import Author


class RankedEvidence(BaseModel):
    """Normalized evidence item enhanced with categorical ranking metadata."""

    title: str
    url: str
    snippet: Optional[str] = None
    source_name: Optional[str] = None
    published_at: Optional[str] = None
    search_query: Optional[str] = None

    # Categorical ranking dimensions
    source_quality: Literal["high", "medium", "low", "unknown"] = "unknown"
    relevance: Literal["high", "medium", "low"] = "medium"
    directness: Literal["direct", "indirect", "contextual"] = "contextual"
    relationship: Literal[
        "supports", "contradicts", "contextual", "unclear",
        "supporting", "contradicting", "irrelevant",
    ] = "unclear"
    relevance_category: Optional[Literal["irrelevant", "contextual", "relevant", "direct"]] = None

    # source_role distinguishes the original social post from external corroboration.
    # An "original_post" source MUST NOT be treated as independent confirming evidence.
    source_role: Literal["external", "original_post"] = "external"


class ClaimEvidenceSources(BaseModel):
    """Ranked evidence sources retrieved for a specific claim."""

    claim_id: str
    search_query: str = ""
    status: Literal[
        "success", "no_relevant_results", "no_results", "search_failed", "rate_limited"
    ] = "success"
    searches: List[SearchAttempt] = Field(default_factory=list)
    sources: List[RankedEvidence] = Field(default_factory=list)
    error: Optional[Union[Dict[str, Any], str]] = None
    evidence_count: Optional[int] = None


class ClaimAssessment(BaseModel):
    """Structured fact-checking evaluation and verdict for an individual claim."""

    claim_id: str
    claim_text: str
    # verdict is Optional[str] so it can be null when reasoning fails (API error, rate limit)
    # rather than silently coercing a failure into UNVERIFIED.
    verdict: Optional[Literal[
        "SUPPORTED",
        "REFUTED",
        "PARTIALLY_SUPPORTED",
        "MISLEADING",
        "UNVERIFIED",
        "INSUFFICIENT_EVIDENCE",
    ]] = None
    confidence: Optional[Literal["high", "medium", "low"]] = None
    explanation: str = ""
    supporting_evidence: List[RankedEvidence] = Field(default_factory=list)
    contradicting_evidence: List[RankedEvidence] = Field(default_factory=list)
    context: List[str] = Field(default_factory=list)
    # error_type distinguishes system failures from factual uncertainty
    error: Optional[str] = None
    error_type: Optional[Literal["rate_limit", "rate_limited", "api_error", "parse_error", "timeout"]] = None
    reasoning_error_type: Optional[str] = None


class FactCheckAnalysis(BaseModel):
    """Overall fact-checking reasoning summary across all extracted claims."""

    claims: List[ClaimAssessment] = Field(default_factory=list)
    overall_summary: str = ""
    context_flags: List[str] = Field(default_factory=lambda: ["none"])
    claims_analyzed: int = 0


class UnifiedAnalysisData(BaseModel):
    """Normalized unified response payload.

    Canonical structure with zero duplication:
    data
     ├── source
     ├── author
     ├── content (text, media)
     ├── context (flags)
     ├── claims
     ├── evidence
     └── analysis
    """

    source: SourceInfo
    author: Optional[Author] = None

    # content holds the post text + normalized media list (canonical single source)
    content: Dict[str, Any] = Field(default_factory=dict)

    context: Dict[str, Any] = Field(default_factory=lambda: {"flags": ["none"]})
    claims: List[Claim] = Field(default_factory=list)
    evidence: List[ClaimEvidenceSources] = Field(default_factory=list)
    analysis: FactCheckAnalysis


class UnifiedAnalysisResponse(BaseModel):
    """Unified API envelope response returned by POST /api/v1/analyze."""

    status: str = "success"
    data: UnifiedAnalysisData
