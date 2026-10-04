"""Claim Extraction Service.

Identifies factual, externally verifiable claims and contextual flags (such as satire/parody)
from normalized social media post content, media text, and visual descriptions using Groq LLM.

Responsibilities:
- Extracts discrete factual assertions that can be fact-checked against external evidence.
- Classifies claim_type: factual | narrative | opinion | satire.
- Detects satire, parody, fictional, hypothetical, or opinion context flags.
- Deduplicates identical claims appearing across post text and image text.
- Filters out non-factual claims (narrative, opinion) from requires_verification.
- Never judges truth/falsity of any claim.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

from groq import AsyncGroq, BadRequestError
from pydantic import ValidationError

from app.core.config import get_settings
from app.core.timing import timed_stage
from app.schemas.analysis import (
    AnalysisInput,
    Claim,
    ClaimExtractionResult,
)

logger = logging.getLogger(__name__)

CLAIM_EXTRACTION_SYSTEM_PROMPT = """You are the claim-extraction component of TruthLens, an automated fact-checking system.

Your task is to identify, prioritize, and extract core assertions from social media content.
Do NOT over-extract claims: extract at most 3–5 of the most important claims (avoid extracting every trivial sentence).

────────────────────────────────────────────────────────────────────────────
CLAIM PRIORITY — priority field (PRIMARY vs SECONDARY vs NARRATIVE)
────────────────────────────────────────────────────────────────────────────
Assign exactly one priority to each extracted claim:

• "primary":
  The MAIN factual assertion that the post is trying to communicate (the central premise or headline event).
  Typically 1–2 claims per post.

• "secondary":
  Important supporting factual assertions that materially contribute to the story
  (e.g., specific actions or statements attributed to other official figures or institutions).

• "narrative":
  Filler, humorous details, hypothetical commentary, exaggerated storytelling,
  call to action, audience reactions, or downstream fictional details
  (e.g. "social media users started demanding rankings", "experts said athletes need no shame", "millions of people are confused").

PRIORITY RULES:
- Only "primary" and relevant "secondary" claims should normally go to evidence search.
- "narrative" claims must be retained in the response if useful, but should NOT trigger external evidence searches (requires_verification = false).
- Do NOT classify something as narrative merely because it is difficult to verify.
- Do NOT treat satire itself as proof that a claim is false.

────────────────────────────────────────────────────────────────────────────
────────────────────────────────────────────────────────────────────────────
CLAIM CLASSIFICATION — claim_type field
────────────────────────────────────────────────────────────────────────────
• "factual"              — Discrete assertion of real-world fact that CAN be checked externally.
• "absence_of_evidence"  — Statements asserting that an organization, authority, or public entity has NOT announced, confirmed, or released something, or that no official record/evidence exists (e.g. "The International Olympic Committee has not announced anything officially", "No official statement exists").
• "narrative"            — Story-telling detail, exaggerated description, or humorous filler.
• "opinion"              — Subjective editorial commentary or personal prediction.
• "satire"               — Clearly marked joke/satire/parody that does not correspond to a real-world event.

────────────────────────────────────────────────────────────────────────────
requires_verification RULE
────────────────────────────────────────────────────────────────────────────
• priority in ("primary", "secondary") with claim_type in ("factual", "absence_of_evidence") → requires_verification = true
• priority = "narrative" or claim_type in ("narrative", "opinion", "satire") → requires_verification = false

────────────────────────────────────────────────────────────────────────────
WHAT IS NOT A CLAIM
────────────────────────────────────────────────────────────────────────────
- Do NOT extract questions.
- Do NOT extract calls to action / engagement prompts ("Follow for more", "Share this").
- Do NOT extract hashtags or generic greetings.
- Do NOT extract advertisements or promotional spam.

────────────────────────────────────────────────────────────────────────────
DO NOT JUDGE TRUTH OR FALSITY
────────────────────────────────────────────────────────────────────────────
You are NOT fact-checking. Never judge whether a claim is true, false, likely, or unlikely.
Treat all statements as unverified input to be cataloged for later verification.

────────────────────────────────────────────────────────────────────────────
CONTEXT FLAGS
────────────────────────────────────────────────────────────────────────────
Detect whether the post as a whole shows non-literal signals:
  • "satire"      — explicit disclaimer (e.g. "NOT REAL, ONLY FOR SATIRE") or satirical account
  • "parody"      — humorous exaggeration mocking a specific entity
  • "fictional"   — explicitly framed as fiction or joke
  • "hypothetical" — "What if" scenarios
  • "opinion"     — predominantly editorial
  • "none"        — standard factual/ambiguous content

────────────────────────────────────────────────────────────────────────────
DEDUPLICATION & SOURCE ATTRIBUTION
────────────────────────────────────────────────────────────────────────────
If a claim appears in both post_text and media_text, extract it ONCE with source = "mixed".
Allowed source values: "post_text", "image_text", "video_transcript", "mixed".
Allowed importance values: "high" (central thesis), "medium" (secondary), "low" (minor).

────────────────────────────────────────────────────────────────────────────
TWO-STAGE SEARCH QUERY GENERATION
────────────────────────────────────────────────────────────────────────────
For each claim where requires_verification = true:
1. "primary_query": concise 5–10 word search query preserving the key named entities and event topic (e.g. "Trump Jerk4Krik Olympics announcement").
2. "fallback_queries": up to 2 broader contextual queries for important claims. Remove potentially fictional or unverified specific terms while preserving real-world actors, organizations, event context, and dates.
   - Example fallback 1: "Trump Olympics announcement new sport"
   - Example fallback 2: "Trump 2028 Olympics sports announcement"
   - Do NOT invent a replacement entity; remove the fictional term and keep real-world context.
   - For narrative claims, primary_query and fallback_queries should be empty/null.

────────────────────────────────────────────────────────────────────────────
OUTPUT SCHEMA
────────────────────────────────────────────────────────────────────────────
Return ONLY valid JSON matching this schema:
{
  "context_flags": ["satire" | "parody" | "fictional" | "hypothetical" | "opinion" | "none"],
  "claims": [
    {
      "claim_id": "claim_1",
      "text": "Self-contained factual statement",
      "priority": "primary" | "secondary" | "narrative",
      "claim_type": "factual" | "absence_of_evidence" | "narrative" | "opinion" | "satire",
      "importance": "high" | "medium" | "low",
      "source": "post_text" | "image_text" | "video_transcript" | "mixed",
      "requires_verification": true | false,
      "primary_query": "concise 5-10 word search query or null",
      "fallback_queries": ["broader contextual query 1", "broader contextual query 2"],
      "search_query": "concise 5-10 word search query or null"
    }
  ]
}
"""

CLAIM_STRICT_JSON_SCHEMA: Dict[str, Any] = {
    "name": "ClaimExtractionResult",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "context_flags": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["satire", "parody", "fictional", "hypothetical", "opinion", "none"],
                },
            },
            "claims": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "claim_id": {"type": "string"},
                        "text": {"type": "string"},
                        "priority": {
                            "type": "string",
                            "enum": ["primary", "secondary", "narrative"],
                        },
                        "claim_type": {
                            "type": "string",
                            "enum": ["factual", "absence_of_evidence", "narrative", "opinion", "satire"],
                        },
                        "importance": {
                            "type": "string",
                            "enum": ["high", "medium", "low"],
                        },
                        "source": {
                            "type": "string",
                            "enum": ["post_text", "image_text", "video_transcript", "mixed"],
                        },
                        "requires_verification": {"type": "boolean"},
                        "primary_query": {"type": ["string", "null"]},
                        "fallback_queries": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "search_query": {"type": ["string", "null"]},
                    },
                    "required": [
                        "claim_id", "text", "priority", "claim_type", "importance",
                        "source", "requires_verification", "primary_query", "fallback_queries", "search_query",
                    ],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["context_flags", "claims"],
        "additionalProperties": False,
    },
}

# ── Pre-LLM Rule-Based Helpers ────────────────────────────────────────────────

# Explicit satire/parody signal phrases (lowercase, checked with word boundaries where practical)
# Ordered from strongest to weakest signal.
_SATIRE_KEYWORDS = [
    "not real news",
    "not real",
    "only for satire",
    "purely satirical",
    "meant for entertainment",
    "for entertainment purposes",
    "this is satire",
    "satirical content",
    "satirical post",
    "not a real story",
    "NOT REAL",         # common in image overlays (preserved case for OCR text)
    "FOR SATIRE",
    "parody account",
    "parody post",
    "humor only",
    "not intended as news",
]

_PARODY_KEYWORDS = [
    "parody",
    "this is a parody",
    "parody and satire",
]

_FICTIONAL_KEYWORDS = [
    "fictional",
    "this is fiction",
    "entirely fictional",
]

_OPINION_KEYWORDS = [
    "this is my opinion",
    "in my opinion",
    "personal opinion",
    "opinion piece",
]


def _detect_context_flags_rule_based(
    post_text: str,
    media_text: str,
) -> List[str]:
    """Fast rule-based scan for satire/parody/fiction signals before calling the LLM.

    Combines post caption and image OCR text for maximum coverage.
    Returns a list compatible with ClaimExtractionResult.context_flags.
    """
    combined = f"{post_text} {media_text}".lower()

    flags: List[str] = []

    # Check satire signals
    if any(kw.lower() in combined for kw in _SATIRE_KEYWORDS):
        flags.append("satire")

    # Check parody signals (only add if not already flagged as satire)
    if "satire" not in flags and any(kw.lower() in combined for kw in _PARODY_KEYWORDS):
        flags.append("parody")

    # Check fictional signals
    if any(kw.lower() in combined for kw in _FICTIONAL_KEYWORDS):
        if "fictional" not in flags:
            flags.append("fictional")

    # Check opinion signals
    if any(kw.lower() in combined for kw in _OPINION_KEYWORDS):
        if "opinion" not in flags:
            flags.append("opinion")

    return flags if flags else ["none"]


def _trim_post_text(post_text: str, max_words: int = 600) -> str:
    """Trim post text to a word budget to prevent LLM token overflow.

    The first N words contain the highest claim density. Disclaimers at the
    end are captured by rule-based detection and don't need to go to the LLM.
    """
    if not post_text:
        return ""
    words = post_text.split()
    if len(words) <= max_words:
        return post_text
    trimmed = " ".join(words[:max_words])
    return trimmed + " [text trimmed for length]"


def _merge_flags(
    rule_based: List[str],
    llm_flags: List[str],
) -> List[str]:
    """Merge rule-based and LLM-detected context flags, deduplicating.

    Rule-based flags are treated as authoritative ground truth for explicit
    signals. LLM flags add any additional signals the rules missed.
    """
    merged = list(rule_based)  # start with rule-based (always reliable)
    for f in llm_flags:
        if f != "none" and f not in merged:
            merged.append(f)
    # Remove "none" if any real flag is present
    if any(f != "none" for f in merged):
        merged = [f for f in merged if f != "none"]
    return merged if merged else ["none"]


class ClaimExtractionService:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.groq_api_key or os.getenv("GROQ_API_KEY", "")
        self.model = (
            model
            or settings.groq_claim_model
            or os.getenv("GROQ_CLAIM_MODEL", "openai/gpt-oss-20b")
        )
        self._client: Optional[AsyncGroq] = None

    def _get_client(self) -> AsyncGroq:
        if not self.api_key:
            raise ValueError("GROQ_API_KEY is not configured")
        if self._client is None:
            self._client = AsyncGroq(api_key=self.api_key)
        return self._client

    async def extract_claims(self, analysis_input: AnalysisInput) -> ClaimExtractionResult:
        """Extract verifiable factual claims and context flags from analyzed content."""
        post_text = (analysis_input.post_text or "").strip()
        media_text = (analysis_input.extracted_text or "").strip()
        media_descriptions = [
            m.visual_analysis.description.strip()
            for m in analysis_input.media
            if m.visual_analysis and m.visual_analysis.description
        ]

        # If there is no text and no visual descriptions, return empty result immediately
        if not post_text and not media_text and not media_descriptions:
            return ClaimExtractionResult(context_flags=["none"], items=[])

        # ── Rule-based pre-LLM satire/parody detection ───────────────────────
        # This is a fast-path safety net.  Even if the LLM misses the flag,
        # we inject it so the pipeline handles the post correctly.
        pre_detected_flags = _detect_context_flags_rule_based(
            post_text=post_text, media_text=media_text
        )

        # ── Token budget guard ───────────────────────────────────────────────
        # Trim post text sent to LLM to avoid token overflow.
        # Long posts (>800 words) are trimmed to the first 600 words because
        # the claim-density is highest at the start and the disclaimer at the
        # end is already captured by rule-based detection above.
        trimmed_post_text = _trim_post_text(post_text, max_words=600)

        payload = {
            "post_text": trimmed_post_text or None,
            "media_text": media_text or None,
            "media_descriptions": media_descriptions or None,
            "transcript": None,
            # Tell the model what the rule-based pass found so it can confirm
            "pre_detected_context": pre_detected_flags if pre_detected_flags != ["none"] else None,
        }

        try:
            async with timed_stage("CLAIM_EXTRACTION") as stage:
                result = await self._call_llm(payload)

                # ── Merge rule-based flags into LLM result ───────────────────
                # If rule-based detected satire/parody and LLM returned ["none"],
                # override — the rule-based signal is highly reliable.
                if pre_detected_flags != ["none"]:
                    merged_flags = _merge_flags(pre_detected_flags, result.context_flags)
                    if merged_flags != result.context_flags:
                        logger.info(
                            "[CLAIM_EXTRACTION] Overriding LLM context_flags %s with merged %s "
                            "(rule-based detected: %s)",
                            result.context_flags, merged_flags, pre_detected_flags,
                        )
                    result = ClaimExtractionResult(
                        context_flags=merged_flags,
                        items=result.items,
                        error=result.error,
                    )

                stage.metadata["claims"] = len(result.items)
                stage.metadata["context_flags"] = ",".join(result.context_flags)
                stage.metadata["factual_claims"] = sum(
                    1 for c in result.items if c.claim_type == "factual"
                )
                stage.metadata["pre_detected_flags"] = ",".join(pre_detected_flags)
                return result
        except Exception as exc:
            logger.error("Claim extraction failed: %s", exc)
            # Even on LLM failure, return rule-based flags so context is preserved
            return ClaimExtractionResult(
                context_flags=pre_detected_flags,  # type: ignore[arg-type]
                items=[],
                error=f"Claim extraction failed: {exc}",
            )

    async def _call_llm(self, payload: Dict[str, Any]) -> ClaimExtractionResult:
        """Invoke Groq LLM with strict structured output format."""
        client = self._get_client()

        user_content = (
            f"Extract verifiable claims and context flags from this social media content:\n\n"
            f"{json.dumps(payload, indent=2)}"
        )

        messages = [
            {"role": "system", "content": CLAIM_EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

        content = None
        # 1. Attempt strict json_schema format
        try:
            response = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={"type": "json_schema", "json_schema": CLAIM_STRICT_JSON_SCHEMA},
            )
            content = response.choices[0].message.content
        except (BadRequestError, Exception) as exc:
            logger.info(
                "json_schema format failed for claim extraction; falling back to json_object: %s", exc
            )
            try:
                response = await client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    response_format={"type": "json_object"},
                )
                content = response.choices[0].message.content
            except Exception as fallback_exc:
                logger.warning("Groq claim extraction completion failed: %s", fallback_exc)
                return ClaimExtractionResult(
                    context_flags=["none"],
                    items=[],
                    error=f"Groq claim completion error: {fallback_exc}",
                )

        if not content:
            return ClaimExtractionResult(
                context_flags=["none"],
                items=[],
                error="Empty response received from claim extraction model",
            )

        # 2. Parse and normalize output
        try:
            data = json.loads(content)
            return self._normalize_and_validate(data)
        except (json.JSONDecodeError, ValidationError, Exception) as exc:
            logger.warning(
                "Failed to parse claim extraction output: %s (content: %r)", exc, content[:200]
            )
            return ClaimExtractionResult(
                context_flags=["none"],
                items=[],
                error=f"Invalid claim extraction format: {exc}",
            )

    @staticmethod
    def _normalize_and_validate(data: Dict[str, Any]) -> ClaimExtractionResult:
        """Validate, deduplicate, and assign sequential claim IDs."""
        raw_flags = data.get("context_flags") or []
        valid_flags = {"satire", "parody", "fictional", "hypothetical", "opinion", "none"}
        normalized_flags: List[str] = []

        if isinstance(raw_flags, list):
            for f in raw_flags:
                f_str = str(f).lower().strip()
                if f_str in valid_flags and f_str not in normalized_flags:
                    normalized_flags.append(f_str)

        # If non-none flags exist, remove "none"; if empty, default to ["none"]
        if any(f != "none" for f in normalized_flags):
            normalized_flags = [f for f in normalized_flags if f != "none"]
        elif not normalized_flags:
            normalized_flags = ["none"]

        raw_claims = data.get("claims") or []
        items: List[Claim] = []
        seen_texts: set[str] = set()

        if isinstance(raw_claims, list):
            for idx, c in enumerate(raw_claims, start=1):
                if not isinstance(c, dict):
                    continue
                text = str(c.get("text") or "").strip()
                if not text:
                    continue

                # Deduplicate identical/case-insensitive claim text
                normalized_text_key = " ".join(text.lower().split())
                if normalized_text_key in seen_texts:
                    continue
                seen_texts.add(normalized_text_key)

                # claim_type
                claim_type = c.get("claim_type")
                if claim_type not in ("factual", "absence_of_evidence", "narrative", "opinion", "satire"):
                    claim_type = "factual"

                # Check for absence of evidence signals
                text_lower = text.lower()
                absence_patterns = [
                    "not announced", "has not announced", "have not announced", "hasn't announced", "haven't announced",
                    "no official", "no evidence exists", "no evidence of", "no proof",
                    "not confirmed", "has not confirmed", "have not confirmed", "hasn't confirmed",
                    "there is no official", "no record of", "never announced", "never confirmed",
                ]
                if any(p in text_lower for p in absence_patterns):
                    if claim_type in ("factual", "absence_of_evidence"):
                        claim_type = "absence_of_evidence"

                importance = c.get("importance")
                if importance not in ("high", "medium", "low"):
                    importance = "medium"

                source = c.get("source")
                if source not in ("post_text", "image_text", "video_transcript", "mixed"):
                    source = "mixed"

                # priority: primary, secondary, narrative
                priority = c.get("priority")
                if priority not in ("primary", "secondary", "narrative"):
                    if claim_type == "narrative":
                        priority = "narrative"
                    elif importance == "high" or idx == 1:
                        priority = "primary"
                    else:
                        priority = "secondary"

                req_verif = c.get("requires_verification", True)
                if not isinstance(req_verif, bool):
                    req_verif = priority != "narrative"

                # Only narrative claims never require verification
                if priority == "narrative" or claim_type == "narrative":
                    req_verif = False

                # Retrieve primary and fallback queries
                primary_query = c.get("primary_query") or c.get("search_query") or None
                if primary_query and not isinstance(primary_query, str):
                    primary_query = None
                if primary_query:
                    primary_query = primary_query.strip() or None

                raw_fallbacks = c.get("fallback_queries") or []
                fallback_queries: List[str] = []
                if isinstance(raw_fallbacks, list):
                    for fb in raw_fallbacks:
                        if isinstance(fb, str) and fb.strip():
                            clean_fb = fb.strip()
                            if clean_fb not in fallback_queries and clean_fb != primary_query:
                                fallback_queries.append(clean_fb)
                # Maximum 2 fallback searches
                fallback_queries = fallback_queries[:2]

                search_query = primary_query
                if not req_verif:
                    primary_query = None
                    fallback_queries = []
                    search_query = None

                claim_id = f"claim_{idx}"
                items.append(
                    Claim(
                        claim_id=claim_id,
                        text=text,
                        priority=priority,
                        claim_type=claim_type,
                        importance=importance,
                        source=source,
                        requires_verification=req_verif,
                        primary_query=primary_query,
                        fallback_queries=fallback_queries,
                        search_query=search_query,
                    )
                )
                # Attach search_query as a transient attribute for backwards compatibility
                items[-1].__dict__["_search_query"] = search_query

        return ClaimExtractionResult(
            context_flags=normalized_flags,  # type: ignore[arg-type]
            items=items,
            error=None,
        )
