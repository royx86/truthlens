"""Fact-Check Reasoning Service for TruthLens pipeline.

Evaluates extracted claims against ranked external evidence and post context using Groq LLM,
producing structured verdicts, confidence assessments, explanations, and overall summaries.

Key improvements:
- Rate limit (429) handling with exponential backoff retry.
- Null verdict on system failures (not UNVERIFIED) to distinguish API errors from factual uncertainty.
- Filtered evidence: only external, non-low-relevance sources passed to LLM.
- Configurable concurrency limit for parallel claim evaluation.
- Explicit reasoning rules about indirect evidence and absence-of-evidence.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

from groq import AsyncGroq, BadRequestError, RateLimitError
from pydantic import ValidationError

from app.core.config import get_settings
from app.schemas.analysis import Claim
from app.schemas.report import (
    ClaimAssessment,
    ClaimEvidenceSources,
    FactCheckAnalysis,
    RankedEvidence,
)

logger = logging.getLogger(__name__)

REASONING_SYSTEM_PROMPT = """You are the fact-checking reasoning engine of TruthLens, an automated verification platform.

Your task is to analyze a factual claim against the provided external evidence and produce a structured, objective evaluation.

════════════════════════════════════════════════════════════════
VERDICT CATEGORIES
════════════════════════════════════════════════════════════════
- "SUPPORTED": Direct, credible evidence from reliable sources confirms the claim as stated.
- "REFUTED": Credible evidence directly disproves or debunks the claim.
- "PARTIALLY_SUPPORTED": Some aspects verified but key parts unconfirmed, exaggerated, or inaccurate.
- "MISLEADING": Claim contains true elements but creates a false impression through out-of-context framing.
- "UNVERIFIED": Cannot be definitively confirmed or denied based on available reliable reporting.
- "INSUFFICIENT_EVIDENCE": No relevant external evidence found or sources too sparse to judge.

════════════════════════════════════════════════════════════════
CONFIDENCE LEVELS
════════════════════════════════════════════════════════════════
- "high": Multiple high-quality, direct sources clearly align on the verdict.
- "medium": Moderate evidence available or single credible reporting source.
- "low": Limited evidence, ambiguous reporting, or indirect context only.

════════════════════════════════════════════════════════════════
CRITICAL REASONING RULES — YOU MUST FOLLOW THESE
════════════════════════════════════════════════════════════════

RULE 1 — STRICTLY EVIDENCE-GROUNDED:
  Base conclusions ONLY on the supplied evidence items and post context.
  Do NOT fabricate or invent sources, URLs, or external events.
  Do NOT equate "no evidence found" with "false".
  If no relevant evidence was found → use INSUFFICIENT_EVIDENCE, NOT REFUTED.

RULE 2 — ABSENCE CLAIMS & ABSENCE OF EVIDENCE:
  For claims asserting absence (e.g. claim_type = "absence_of_evidence", such as "X has not announced...", "There is no official...", "No evidence exists...", "The organization has not confirmed..."):
  - Prefer authoritative/official institutional sources (e.g. official IOC/Olympics sources, government records, official press releases).
  - The reasoning model must NOT conclude: "search returned nothing → definitely false".
  - If no relevant official announcement was located in the searched sources, state clearly in the explanation:
    "No relevant official announcement was located in the searched sources."
  - For standard affirmative claims where no evidence was located, use INSUFFICIENT_EVIDENCE or UNVERIFIED (do NOT conclude REFUTED without direct refuting evidence).

RULE 3 — INDIRECT EVIDENCE RULE:
  A source with directness = "indirect" or directness = "contextual" CANNOT alone
  produce a REFUTED or SUPPORTED verdict with "high" confidence.
  Indirect evidence may only contribute to PARTIALLY_SUPPORTED, UNVERIFIED, or MISLEADING.

  EXAMPLE (incorrect reasoning — DO NOT DO THIS):
    Evidence: Article titled "No, Putin did not call Trump a genius" (about a different event/context)
    Claim: "Putin praised Trump for the Jerk4Krik idea, calling him a genius"
    Wrong: Treat the Putin-genius article as direct refutation of the specific claim.
    Correct: The article addresses a different event; it is indirect context only.
    Use UNVERIFIED or INSUFFICIENT_EVIDENCE with an explanation noting the difference.

RULE 4 — HISTORICAL/GENERAL ≠ SPECIFIC:
  Do NOT use an article about a historically different event as direct evidence for or
  against a new specific claim merely because the wording or entities are similar.
  Always note the distinction in your explanation.

RULE 5 — SATIRE CONTEXT ≠ FACTUAL PROOF:
  If the post context contains signals/flags of satire or parody (e.g., flags=["satire"]),
  clearly note this in explanation and context list.
  CRITICAL RULE: Satire context alone does NOT constitute proof that an individual claim is factually false.
  Do NOT automatically conclude REFUTED solely because the surrounding post is satirical.
  If there is no external evidence confirming or disproving the claim:
  You MUST use INSUFFICIENT_EVIDENCE or UNVERIFIED (never REFUTED without direct refuting evidence).
  Preserve contextual signals separately in the context list.

RULE 6 — SOURCE ROLE:
  Evidence items marked source_role = "original_post" are the ORIGINAL CLAIM SOURCE.
  They are NOT independent corroborating evidence. Never use them to "support" a claim.
  Only use them for contextual framing.

════════════════════════════════════════════════════════════════
OUTPUT FORMAT
════════════════════════════════════════════════════════════════
Return ONLY a valid JSON object:
{
  "verdict": "SUPPORTED" | "REFUTED" | "PARTIALLY_SUPPORTED" | "MISLEADING" | "UNVERIFIED" | "INSUFFICIENT_EVIDENCE",
  "confidence": "high" | "medium" | "low",
  "explanation": "<Concise, neutral 2–4 sentence explanation referencing the evidence>",
  "supporting_evidence_indices": [<0-based indices of external evidence items that support the claim>],
  "contradicting_evidence_indices": [<0-based indices of external evidence items that contradict>],
  "context": ["<Specific contextual note 1>", "..."]
}
"""


def _classify_error_type(exc: Exception) -> str:
    """Classify a Groq API exception into a clean error_type string."""
    if isinstance(exc, RateLimitError):
        return "rate_limit"
    exc_str = str(exc).lower()
    if "rate" in exc_str and ("limit" in exc_str or "429" in exc_str):
        return "rate_limit"
    if "timeout" in exc_str or "timed out" in exc_str:
        return "timeout"
    return "api_error"


class ReasoningService:
    """Service to execute fact-checking reasoning using Groq LLM."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        cfg = get_settings()
        self.api_key = api_key or cfg.groq_api_key or os.environ.get("GROQ_API_KEY", "")
        self.model = model or cfg.groq_reasoning_model
        self.max_retries = cfg.reasoning_max_retries
        self.retry_base_delay = cfg.reasoning_retry_base_delay
        self.max_concurrency = cfg.reasoning_max_concurrency
        self.max_evidence_per_claim = cfg.reasoning_max_evidence_per_claim
        self._client: Optional[AsyncGroq] = None
        self._semaphore: Optional[asyncio.Semaphore] = None

    @property
    def client(self) -> AsyncGroq:
        if self._client is None:
            if not self.api_key:
                raise ValueError("GROQ_API_KEY is not configured.")
            self._client = AsyncGroq(api_key=self.api_key)
        return self._client

    @property
    def semaphore(self) -> asyncio.Semaphore:
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.max_concurrency)
        return self._semaphore

    def _filter_evidence_for_reasoning(
        self, sources: List[RankedEvidence]
    ) -> List[RankedEvidence]:
        """Filter evidence before sending to reasoning LLM to reduce token usage.

        Rules:
        - Exclude original_post sources (they are not independent evidence).
        - Exclude relevance="low" sources (too noisy for reasoning).
        - Exclude relevance_category="irrelevant" sources.
        - NEVER fall back to including low-relevance or irrelevant sources when relevant_count == 0.
        - Limit total count to max_evidence_per_claim.
        """
        filtered = [
            s for s in sources
            if s.source_role == "external"
            and s.relevance != "low"
            and getattr(s, "relevance_category", None) != "irrelevant"
        ]
        return filtered[: self.max_evidence_per_claim]

    async def _call_with_retry(self, messages: List[Dict[str, Any]]) -> Optional[str]:
        """Call LLM with exponential backoff retry on rate limit errors.

        Returns raw content string or raises the last exception.
        """
        last_exc: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    response_format={"type": "json_object"},
                    temperature=0.1,
                )
                return response.choices[0].message.content or "{}"

            except RateLimitError as exc:
                last_exc = exc
                wait = self.retry_base_delay * (2 ** (attempt - 1))
                logger.warning(
                    f"[TRUTHLENS] [REASONING] RATE_LIMIT attempt={attempt}/{self.max_retries} "
                    f"wait={wait:.1f}s"
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(wait)

            except Exception as exc:
                # Non-rate-limit errors: do not retry
                raise exc

        raise last_exc  # type: ignore[misc]

    async def evaluate_claim(
        self,
        claim: Claim,
        claim_evidence: ClaimEvidenceSources,
        context_flags: List[str],
        post_context: Optional[str] = None,
        media_context: Optional[str] = None,
    ) -> ClaimAssessment:
        """Evaluate a single claim against its ranked evidence using LLM reasoning."""
        start_time = time.perf_counter()
        claim_id = claim.claim_id
        logger.info(f"[TRUTHLENS] [REASONING] START claim_id={claim_id} model={self.model}")

        # Claims that are narrative or don't require verification: skip LLM
        priority = getattr(claim, "priority", "primary")
        if priority == "narrative" or not claim.requires_verification:
            duration = time.perf_counter() - start_time
            logger.info(
                f"[TRUTHLENS] [REASONING] SKIPPED claim_id={claim_id} "
                f"reason='priority={priority}, requires_verification={claim.requires_verification}' "
                f"duration={duration:.2f}s"
            )
            return ClaimAssessment(
                claim_id=claim_id,
                claim_text=claim.text,
                verdict="UNVERIFIED",
                confidence="low",
                explanation=(
                    f"Claim classified as narrative detail / commentary ({claim.claim_type}) — "
                    "retained for context without triggering external evidence verification."
                ),
                context=[f"Claim priority: {priority}."],
            )

        # Provider search failures must NOT be converted into factual verdicts
        if getattr(claim_evidence, "status", None) in ("search_failed", "rate_limited"):
            duration = time.perf_counter() - start_time
            err_msg = (
                claim_evidence.error.get("message", "Search provider error")
                if isinstance(claim_evidence.error, dict)
                else str(claim_evidence.error or "Search provider error")
            )
            logger.warning(
                f"[TRUTHLENS] [REASONING] PROVIDER_FAILURE claim_id={claim_id} "
                f"status={claim_evidence.status} error={err_msg!r}"
            )
            err_type = "rate_limited" if claim_evidence.status == "rate_limited" else "api_error"
            return ClaimAssessment(
                claim_id=claim_id,
                claim_text=claim.text,
                verdict=None,  # Null verdict: provider failure must NOT become a factual verdict!
                confidence=None,
                explanation=f"Evidence search was unavailable ({claim_evidence.status}); factual evaluation could not be completed.",
                error=err_msg,
                error_type=err_type,
                reasoning_error_type=err_type,
            )

        # Filter evidence: exclude original_post and low-relevance sources
        filtered_sources = self._filter_evidence_for_reasoning(claim_evidence.sources)

        # Format filtered evidence for the prompt
        evidence_snippets = []
        for idx, ev in enumerate(filtered_sources):
            evidence_snippets.append(
                f"[{idx}] Title: {ev.title}\n"
                f"    URL: {ev.url}\n"
                f"    Source: {ev.source_name or 'unknown'} "
                f"(Quality: {ev.source_quality}, Relevance: {ev.relevance}, "
                f"Directness: {ev.directness})\n"
                f"    Snippet: {ev.snippet or 'No snippet available'}\n"
                f"    Relationship: {ev.relationship} | Role: {ev.source_role}"
            )

        original_post_count = sum(
            1 for s in claim_evidence.sources if s.source_role == "original_post"
        )
        skipped_low_rel = len(claim_evidence.sources) - original_post_count - len(filtered_sources)

        evidence_text = (
            "\n\n".join(evidence_snippets)
            if evidence_snippets
            else "No relevant external evidence sources found."
        )

        user_prompt = f"""CLAIM TO EVALUATE:
ID: {claim.claim_id}
Statement: "{claim.text}"
Claim Type: {claim.claim_type}
Importance: {claim.importance}
Source in Post: {claim.source}

POST CONTEXT FLAGS:
{', '.join(context_flags) if context_flags else 'none'}

ORIGINAL POST TEXT (context only — NOT independent evidence):
{post_context[:500] if post_context else 'N/A'}

VISUAL/MEDIA CONTEXT:
{media_context or 'N/A'}

EXTERNAL EVIDENCE ({len(filtered_sources)} sources shown; {original_post_count} original_post sources excluded; {skipped_low_rel} low-relevance sources excluded):
{evidence_text}

REMINDER — ABSENCE CLAIMS & ABSENCE OF EVIDENCE:
If this claim asserts absence (claim_type="absence_of_evidence"): Prefer authoritative official sources. Do NOT conclude "search returned nothing → definitely false". State: "No relevant official announcement was located in the searched sources."
For affirmative claims with no evidence found, use INSUFFICIENT_EVIDENCE or UNVERIFIED. Do NOT use REFUTED just because no confirming source was found.

REMINDER — SATIRE CONTEXT ≠ FACTUAL PROOF:
Satire context (e.g., flags=["satire"]) does NOT prove that an individual claim is factually false.
If there is no external evidence, you must use INSUFFICIENT_EVIDENCE or UNVERIFIED, not REFUTED.

REMINDER — INDIRECT EVIDENCE:
Sources marked directness="indirect" or directness="contextual" cannot alone produce REFUTED or SUPPORTED with high confidence.

Provide the structured fact-checking JSON assessment for this claim.
"""

        try:
            async with self.semaphore:
                raw_content = await self._call_with_retry(
                    messages=[
                        {"role": "system", "content": REASONING_SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ]
                )

            parsed = json.loads(raw_content or "{}")

            verdict = parsed.get("verdict")
            valid_verdicts = {
                "SUPPORTED", "REFUTED", "PARTIALLY_SUPPORTED",
                "MISLEADING", "UNVERIFIED", "INSUFFICIENT_EVIDENCE",
            }
            if verdict not in valid_verdicts:
                verdict = "UNVERIFIED"

            confidence = parsed.get("confidence", "low")
            if confidence not in ("high", "medium", "low"):
                confidence = "low"

            # Enforce: indirect-only evidence cannot yield high confidence
            all_indirect = all(
                ev.directness in ("indirect", "contextual") for ev in filtered_sources
            ) if filtered_sources else True
            if all_indirect and confidence == "high":
                confidence = "medium"
                logger.info(
                    f"[TRUTHLENS] [REASONING] CONFIDENCE_DOWNGRADED claim_id={claim_id} "
                    f"reason='all_evidence_indirect'"
                )

            explanation = parsed.get("explanation", "Assessment completed based on available evidence.")
            context_list = parsed.get("context", [])
            if not isinstance(context_list, list):
                context_list = [str(context_list)]

            # Absence of evidence claims requirement: must clearly note search limitation
            if claim.claim_type == "absence_of_evidence":
                if "official announcement was located" not in explanation.lower():
                    explanation = f"No relevant official announcement was located in the searched sources. {explanation}".strip()

            # Affirmative claims with zero relevant evidence: must be INSUFFICIENT_EVIDENCE
            if not filtered_sources and verdict not in ("INSUFFICIENT_EVIDENCE", "UNVERIFIED"):
                verdict = "INSUFFICIENT_EVIDENCE"
                confidence = "low"

            # Map indices to actual filtered_sources items
            supp_indices = parsed.get("supporting_evidence_indices", [])
            contra_indices = parsed.get("contradicting_evidence_indices", [])

            supporting_evidence: List[RankedEvidence] = []
            for i in supp_indices:
                if isinstance(i, int) and 0 <= i < len(filtered_sources):
                    ev = filtered_sources[i]
                    # Never count original_post as supporting evidence
                    if ev.source_role == "external":
                        supporting_evidence.append(ev)

            contradicting_evidence: List[RankedEvidence] = []
            for i in contra_indices:
                if isinstance(i, int) and 0 <= i < len(filtered_sources):
                    ev = filtered_sources[i]
                    if ev.source_role == "external":
                        contradicting_evidence.append(ev)

            # Fallback relationship mapping if LLM returned empty indices
            if not supporting_evidence and not contradicting_evidence:
                for ev in filtered_sources:
                    if ev.source_role == "external" and ev.relationship == "supports":
                        supporting_evidence.append(ev)
                    elif ev.source_role == "external" and ev.relationship == "contradicts":
                        contradicting_evidence.append(ev)

            duration = time.perf_counter() - start_time
            logger.info(
                f"[TRUTHLENS] [REASONING] END claim_id={claim_id} verdict={verdict} "
                f"confidence={confidence} evidence_used={len(filtered_sources)} "
                f"duration={duration:.2f}s"
            )

            return ClaimAssessment(
                claim_id=claim_id,
                claim_text=claim.text,
                verdict=verdict,
                confidence=confidence,
                explanation=explanation,
                supporting_evidence=supporting_evidence,
                contradicting_evidence=contradicting_evidence,
                context=context_list,
            )

        except Exception as exc:
            duration = time.perf_counter() - start_time
            error_msg = str(exc).replace("\n", " ")
            error_type = _classify_error_type(exc)

            logger.error(
                f"[TRUTHLENS] [REASONING] ERROR claim_id={claim_id} "
                f"error_type={error_type} duration={duration:.2f}s error={error_msg!r}"
            )

            # CRITICAL: Do NOT convert an API failure into UNVERIFIED.
            # verdict=None signals a system failure, not factual uncertainty.
            return ClaimAssessment(
                claim_id=claim_id,
                claim_text=claim.text,
                verdict=None,        # null = system failure
                confidence=None,
                explanation=f"Fact-check reasoning could not complete: {error_msg}",
                context=["Reasoning service error encountered."],
                error=error_msg,
                error_type=error_type,
                reasoning_error_type="rate_limited" if error_type == "rate_limit" else error_type,
            )

    async def evaluate_claims(
        self,
        claims: List[Claim],
        evidence_by_claim: List[ClaimEvidenceSources],
        context_flags: List[str],
        post_context: Optional[str] = None,
        media_context: Optional[str] = None,
    ) -> FactCheckAnalysis:
        """Evaluate multiple claims concurrently (bounded by semaphore) and produce overall report."""
        start_all = time.perf_counter()
        logger.info(
            f"[TRUTHLENS] [REASONING] START_ALL claims={len(claims)} model={self.model}"
        )

        evidence_map: Dict[str, ClaimEvidenceSources] = {
            item.claim_id: item for item in evidence_by_claim
        }

        async def _evaluate_one(claim: Claim) -> ClaimAssessment:
            ev_sources = evidence_map.get(
                claim.claim_id,
                ClaimEvidenceSources(claim_id=claim.claim_id, search_query="", sources=[]),
            )
            return await self.evaluate_claim(
                claim=claim,
                claim_evidence=ev_sources,
                context_flags=context_flags,
                post_context=post_context,
                media_context=media_context,
            )

        assessments = await asyncio.gather(*[_evaluate_one(c) for c in claims])

        overall_summary = self._generate_overall_summary(list(assessments), context_flags)
        total_duration = time.perf_counter() - start_all

        failed_count = sum(1 for a in assessments if a.verdict is None)
        logger.info(
            f"[TRUTHLENS] [REASONING] SUMMARY claims={len(claims)} "
            f"failed={failed_count} duration={total_duration:.2f}s"
        )

        return FactCheckAnalysis(
            claims=list(assessments),
            overall_summary=overall_summary,
            context_flags=context_flags,
            claims_analyzed=len(assessments),
        )

    def _generate_overall_summary(
        self,
        assessments: List[ClaimAssessment],
        context_flags: List[str],
    ) -> str:
        """Construct a neutral, concise executive summary from claim assessments."""
        if not assessments:
            if "satire" in context_flags:
                return "The post was identified as satirical; no verifiable factual claims were found."
            return "No verifiable factual claims were identified in the analyzed content."

        verdicts = [a.verdict for a in assessments]
        total = len(assessments)
        failed = sum(1 for v in verdicts if v is None)
        refuted_count = verdicts.count("REFUTED")
        supported_count = verdicts.count("SUPPORTED")
        misleading_count = verdicts.count("MISLEADING")
        partially_count = verdicts.count("PARTIALLY_SUPPORTED")
        unverified_count = sum(
            1 for v in verdicts if v in ("UNVERIFIED", "INSUFFICIENT_EVIDENCE")
        )

        summary_parts = []
        if "satire" in context_flags:
            summary_parts.append(
                "This post contains explicit signals or context of satire/parody."
            )

        if failed == total:
            summary_parts.append(
                f"Reasoning could not complete for any of the {total} claim(s) due to system errors."
            )
        elif refuted_count == total - failed:
            summary_parts.append(
                f"All {total - failed} analyzed claim(s) were refuted by external evidence."
            )
        elif supported_count == total - failed:
            summary_parts.append(
                f"All {total - failed} analyzed claim(s) are supported by credible reporting."
            )
        else:
            details = []
            if supported_count:
                details.append(f"{supported_count} supported")
            if refuted_count:
                details.append(f"{refuted_count} refuted")
            if misleading_count:
                details.append(f"{misleading_count} misleading")
            if partially_count:
                details.append(f"{partially_count} partially supported")
            if unverified_count:
                details.append(f"{unverified_count} unverified/insufficient evidence")
            if failed:
                details.append(f"{failed} reasoning failed (system error)")

            summary_parts.append(f"Analysis of {total} claim(s): {', '.join(details)}.")

        return " ".join(summary_parts)
