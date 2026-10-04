"""Evidence Ranking Service for TruthLens pipeline.

Ranks and categorizes retrieved external evidence based on source quality,
relevance, directness, and relationship to the claim without assigning fake truth scores.

Key rules enforced here:
- source_role="original_post" sources are NEVER treated as independent supporting/contradicting
  evidence; they are preserved as "contextual" relationship with relevance="low".
- relevance="low" sources cannot produce strong verdicts.
- directness="indirect" / directness="contextual" sources cannot automatically refute a claim.
"""

from __future__ import annotations

import logging
import re
import time
import urllib.parse
from typing import Any, Dict, List, Literal, Optional

from app.schemas.analysis import Claim
from app.schemas.evidence import ClaimEvidence, Evidence, SearchError
from app.schemas.report import ClaimEvidenceSources, RankedEvidence

logger = logging.getLogger(__name__)

# Known high-reputation domains (fact-checkers, wire services, official institutions)
HIGH_QUALITY_DOMAINS = {
    "reuters.com",
    "apnews.com",
    "bbc.com",
    "bbc.co.uk",
    "afp.com",
    "factcheck.org",
    "snopes.com",
    "politifact.com",
    "fullfact.org",
    "leadstories.com",
    "who.int",
    "un.org",
    "olympics.com",
    "olympic.org",
    "nature.com",
    "science.org",
    "theguardian.com",
    "nytimes.com",
    "wsj.com",
    "washingtonpost.com",
    "bloomberg.com",
    "npr.org",
}

# Recognized mainstream media domains
MEDIUM_QUALITY_DOMAINS = {
    "cnn.com",
    "cnbc.com",
    "forbes.com",
    "time.com",
    "usatoday.com",
    "abcnews.go.com",
    "cbsnews.com",
    "nbcnews.com",
    "thehindu.com",
    "ndtv.com",
    "indianexpress.com",
    "indiatoday.in",
    "aljazeera.com",
    "euronews.com",
    "dw.com",
    "france24.com",
    "axios.com",
    "politico.com",
}

# Low-quality or user-generated sources for fact-checking evidence
LOW_QUALITY_DOMAINS = {
    "facebook.com",
    "instagram.com",
    "twitter.com",
    "x.com",
    "tiktok.com",
    "reddit.com",
    "threads.net",
    "pinterest.com",
    "quora.com",
    "medium.com",
    "blogspot.com",
    "wordpress.com",
}

# Linguistic cues indicating contradiction or refutation
CONTRADICTION_KEYWORDS = [
    r"\bfalse\b",
    r"\bhoax\b",
    r"\bdebunk(ed|s)?\b",
    r"\bno\s+evidence\b",
    r"\bnever\s+happened\b",
    r"\bfake\b",
    r"\bparody\b",
    r"\bsatire\b",
    r"\bsatirical\b",
    r"\bmisinformation\b",
    r"\bdisinformation\b",
    r"\bdeni(es|ed)\b",
    r"\brefut(es|ed)\b",
    r"\buntrue\b",
    r"\bincorrect\b",
    r"\bdistorted\b",
]

# Linguistic cues indicating support or confirmation
SUPPORT_KEYWORDS = [
    r"\bconfirm(s|ed)?\b",
    r"\bannounced\b",
    r"\bofficially\b",
    r"\bverified\b",
    r"\btrue\b",
    r"\bapproved\b",
    r"\bstatement\s+confirms\b",
    r"\bpassed\b",
    r"\bsigned\s+into\s+law\b",
]


class EvidenceRankingService:
    """Evaluates and ranks evidence items for claims using categorical dimensions."""

    def evaluate_source_quality(self, url: str) -> Literal["high", "medium", "low", "unknown"]:
        """Assess the intrinsic credibility of the evidence host domain."""
        if not url:
            return "unknown"
        try:
            domain = urllib.parse.urlparse(url).netloc.lower()
            if domain.startswith("www."):
                domain = domain[4:]

            # Institutional top-level domains
            if domain.endswith(".gov") or domain.endswith(".edu") or domain.endswith(".mil"):
                return "high"

            for high_domain in HIGH_QUALITY_DOMAINS:
                if domain == high_domain or domain.endswith("." + high_domain):
                    return "high"

            for med_domain in MEDIUM_QUALITY_DOMAINS:
                if domain == med_domain or domain.endswith("." + med_domain):
                    return "medium"

            for low_domain in LOW_QUALITY_DOMAINS:
                if domain == low_domain or domain.endswith("." + low_domain):
                    return "low"

            return "unknown"
        except Exception:
            return "unknown"

    def evaluate_relevance(
        self, claim_text: str, title: str, snippet: Optional[str]
    ) -> Literal["high", "medium", "low"]:
        """Assess lexical and entity relevance of the evidence to the claim."""
        combined_text = f"{title or ''} {snippet or ''}".lower()
        if not combined_text.strip():
            return "low"

        claim_words = [
            w.lower()
            for w in re.findall(r"\b\w{3,}\b", claim_text)
            if w.lower() not in {"the", "and", "that", "this", "with", "from", "for", "are", "was"}
        ]
        if not claim_words:
            return "medium"

        matched = sum(1 for w in claim_words if w in combined_text)
        ratio = matched / len(claim_words)

        if ratio >= 0.5:
            return "high"
        elif ratio >= 0.25:
            return "medium"
        return "low"

    def evaluate_directness(
        self, relevance: str, title: str, snippet: Optional[str]
    ) -> Literal["direct", "indirect", "contextual"]:
        """Assess how directly the evidence addresses the core claim statement.

        IMPORTANT: Only high-relevance items with sufficient text are "direct".
        Medium-relevance items are "indirect" — they may provide context but cannot
        alone produce a strong refutation or support verdict.
        """
        combined = f"{title or ''} {snippet or ''}".lower()
        if relevance == "high" and len(combined) > 30:
            return "direct"
        elif relevance == "medium":
            return "indirect"
        return "contextual"

    def evaluate_relationship(
        self,
        claim_text: str,
        title: str,
        snippet: Optional[str],
        source_role: str = "external",
    ) -> Literal["supports", "contradicts", "contextual", "unclear"]:
        """Determine whether the evidence supports, contradicts, or provides context.

        CRITICAL RULE: An "original_post" source_role MUST return "contextual".
        The post itself asserting X is NOT independent evidence that X is true.
        """
        # Original post can never be treated as independent supporting/contradicting evidence
        if source_role == "original_post":
            return "contextual"

        combined = f"{title or ''} {snippet or ''}".lower()
        if not combined.strip():
            return "unclear"

        has_contradiction = any(re.search(pat, combined) for pat in CONTRADICTION_KEYWORDS)
        has_support = any(re.search(pat, combined) for pat in SUPPORT_KEYWORDS)

        if has_contradiction:
            return "contradicts"
        elif has_support:
            return "supports"
        elif len(combined) > 20:
            return "contextual"
        return "unclear"

    def rank_evidence_item(self, claim_text: str, item: Evidence) -> RankedEvidence:
        """Evaluate an individual Evidence item and return a RankedEvidence model."""
        source_role = getattr(item, "source_role", "external")

        source_quality = self.evaluate_source_quality(item.url)

        # For original_post items: cap source_quality at "low", relevance="low",
        # directness="contextual". This ensures they never boost verdict confidence.
        if source_role == "original_post":
            relevance: Literal["high", "medium", "low"] = "low"
            directness: Literal["direct", "indirect", "contextual"] = "contextual"
            relationship: Literal["supports", "contradicts", "contextual", "unclear"] = "contextual"
            if source_quality not in ("low", "unknown"):
                source_quality = "low"
        else:
            relevance = self.evaluate_relevance(claim_text, item.title, item.snippet)
            directness = self.evaluate_directness(relevance, item.title, item.snippet)
            relationship = self.evaluate_relationship(
                claim_text, item.title, item.snippet, source_role=source_role
            )

        return RankedEvidence(
            title=item.title,
            url=item.url,
            snippet=item.snippet,
            source_name=item.source_name,
            published_at=item.published_at,
            search_query=item.search_query,
            source_quality=source_quality,
            relevance=relevance,
            directness=directness,
            relationship=relationship,
            source_role=source_role,
            relevance_category=getattr(item, "relevance_category", None),
        )

    def rank_claim_evidence(self, claim_evidence: ClaimEvidence) -> ClaimEvidenceSources:
        """Rank and sort all evidence items for a single claim."""
        start_time = time.perf_counter()
        claim_id = claim_evidence.claim_id
        logger.info(f"[TRUTHLENS] [EVIDENCE_RANKING] START claim_id={claim_id}")

        ranked_items: List[RankedEvidence] = []
        for ev in claim_evidence.evidence:
            ranked_items.append(self.rank_evidence_item(claim_evidence.claim_text, ev))

        # Sort: external + high quality + high relevance first; original_post always last
        quality_score = {"high": 3, "medium": 2, "unknown": 1, "low": 0}
        relevance_score = {"high": 3, "medium": 2, "low": 1}
        directness_score = {"direct": 3, "indirect": 2, "contextual": 1}
        role_score = {"external": 1, "original_post": 0}

        ranked_items.sort(
            key=lambda x: (
                role_score.get(x.source_role, 0),
                quality_score.get(x.source_quality, 0),
                relevance_score.get(x.relevance, 0),
                directness_score.get(x.directness, 0),
            ),
            reverse=True,
        )

        # Log how many items are original_post vs external
        original_post_count = sum(1 for r in ranked_items if r.source_role == "original_post")
        external_count = len(ranked_items) - original_post_count

        duration = time.perf_counter() - start_time
        logger.info(
            f"[TRUTHLENS] [EVIDENCE_RANKING] END claim_id={claim_id} "
            f"ranked={len(ranked_items)} external={external_count} "
            f"original_post={original_post_count} duration={duration:.2f}s"
        )

        # Determine status and normalize error format
        status = getattr(claim_evidence, "status", None)
        error = claim_evidence.error

        if error:
            if isinstance(error, str):
                is_rl = "rate" in error.lower() and "limit" in error.lower() or "429" in error
                error = SearchError(type="rate_limited" if is_rl else "provider_error", message=error)
                status = "rate_limited" if is_rl else "search_failed"
            elif isinstance(error, dict):
                err_type = error.get("type", "provider_error")
                error = SearchError(type=err_type, message=error.get("message", str(error)))
                status = "rate_limited" if err_type == "rate_limited" else "search_failed"
        elif status in ("no_relevant_results", "no_results", "rate_limited", "search_failed"):
            # Explicit status from evidence search service must be preserved
            pass
        elif not ranked_items:
            status = "no_results"
        else:
            status = "success"

        return ClaimEvidenceSources(
            claim_id=claim_id,
            search_query=claim_evidence.search_query,
            status=status,
            searches=getattr(claim_evidence, "searches", []),
            sources=ranked_items,
            error=error,
            evidence_count=len(ranked_items),
        )

    def rank_claims_evidence(
        self,
        claims_evidence: List[ClaimEvidence],
    ) -> List[ClaimEvidenceSources]:
        """Rank evidence collections across multiple claims."""
        return [self.rank_claim_evidence(ce) for ce in claims_evidence]
