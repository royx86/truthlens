"""Pydantic schemas for the Evidence Search phase."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field

from app.schemas.analysis import Claim


class Evidence(BaseModel):
    """Normalized evidence source retrieved from web search."""

    title: str
    url: str
    snippet: Optional[str] = None
    source_name: Optional[str] = None
    published_at: Optional[str] = None
    search_query: Optional[str] = None

    # source_role distinguishes the original social post from external evidence.
    # "original_post" sources must NOT be counted as independent corroboration.
    source_role: Literal["external", "original_post"] = "external"
    source_quality: Literal["high", "medium", "low", "unknown"] = "unknown"
    relevance: Literal["high", "medium", "low"] = "low"
    directness: Literal["direct", "indirect", "contextual"] = "contextual"
    relationship: Literal[
        "supporting", "contradicting", "contextual", "irrelevant", "unclear",
        "supports", "contradicts",
    ] = "unclear"
    relevance_category: Optional[Literal["irrelevant", "contextual", "relevant", "direct"]] = None


class SearchError(dict):
    """Structured search error representing provider failure or rate limiting.

    Inherits from dict so it serializes cleanly as {"type": "...", "message": "..."}
    while also supporting substring membership tests (e.g. 'timeout' in error).
    """

    def __init__(self, type: str, message: str, **kwargs: Any) -> None:
        super().__init__(type=type, message=message, **kwargs)

    def __contains__(self, item: Any) -> bool:
        if super().__contains__(item):
            return True
        msg = str(self.get("message", ""))
        err_type = str(self.get("type", ""))
        return str(item) in msg or str(item) in err_type


class SearchAttempt(BaseModel):
    """An individual search attempt executed as part of two-stage search."""

    query: str
    type: Literal["primary", "fallback"]
    result_count: int
    relevant_count: int = 0


class ClaimEvidence(BaseModel):
    """Collection of evidence items associated with a specific claim."""

    claim_id: str
    claim_text: str
    search_query: str = ""
    status: Literal[
        "success", "no_relevant_results", "no_results", "search_failed", "rate_limited"
    ] = "success"
    searches: List[SearchAttempt] = Field(default_factory=list)
    evidence: List[Evidence] = Field(default_factory=list)
    error: Optional[Union[Dict[str, Any], str]] = None
    claim_type: Optional[str] = "factual"


class EvidenceSearchRequest(BaseModel):
    """Request payload for searching evidence for one or more claims."""

    claims: List[Claim]


class EvidenceSearchResponse(BaseModel):
    """API envelope response containing evidence search results for each claim."""

    status: str = "success"
    results: List[ClaimEvidence] = Field(default_factory=list)
