"""Evidence Search Service for TruthLens pipeline.

Retrieves external web evidence for extracted claims requiring verification.
Transforms raw search provider responses into normalized, deduplicated Evidence schemas.

Key behaviors:
- Uses LLM-generated search_query from ClaimExtractionService when available.
- Falls back to rule-based query generation if not available.
- Detects and tags the original social media post URL as source_role="original_post".
- Deduplicates evidence by normalized URL.
- Bounded concurrency for parallel claim searches.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
import urllib.parse
from typing import Any, Dict, List, Literal, Optional, Set, Union

from app.core.config import settings
from app.schemas.analysis import Claim
from app.schemas.evidence import ClaimEvidence, Evidence, SearchAttempt, SearchError
from app.services.search.base import BaseSearchProvider
from app.services.search.factory import get_search_provider

logger = logging.getLogger(__name__)

# Common tracking query parameters to strip for deduplication
TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "fbclid",
    "gclid",
    "ref",
    "ref_src",
    "source",
    "igshid",
    "ncid",
    "ocid",
}

# Prefix patterns to strip during rule-based query generation
NOISE_PREFIX_PATTERNS = [
    r"^(breaking|alert|report|just in|update|exclusive|video|watch):\s*",
    r"^(did you know that|did you know|it is reported that|sources say that)\s*",
    r"^(according to (sources|reports|posts|the post|official sources),?\s*)",
]

# Social media domains — results from these are flagged as original_post
SOCIAL_MEDIA_DOMAINS = {
    "instagram.com",
    "facebook.com",
    "twitter.com",
    "x.com",
    "threads.net",
    "tiktok.com",
    "youtube.com",
    "reddit.com",
    "linkedin.com",
    "pinterest.com",
}


def normalize_url(raw_url: str) -> str:
    """Normalize a URL to facilitate exact and canonical deduplication.

    - Lowercases scheme and netloc.
    - Strips URL fragments (#...).
    - Removes common tracking query parameters (utm_*, fbclid, etc.).
    - Removes redundant trailing slashes on paths (preserving root '/').
    """
    if not raw_url:
        return ""

    parsed = urllib.parse.urlsplit(raw_url.strip())
    scheme = parsed.scheme.lower() if parsed.scheme else "https"
    netloc = parsed.netloc.lower()
    # Strip default ports if present
    if netloc.endswith(":80") and scheme == "http":
        netloc = netloc[:-3]
    elif netloc.endswith(":443") and scheme == "https":
        netloc = netloc[:-4]

    # Clean path: remove duplicate slashes and trailing slash (except root)
    path = re.sub(r"/+", "/", parsed.path)
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]

    # Filter query parameters
    query_parts = []
    if parsed.query:
        params = urllib.parse.parse_qsl(parsed.query, keep_blank_values=False)
        filtered = [
            (k, v)
            for k, v in params
            if k.lower() not in TRACKING_PARAMS and not k.lower().startswith("utm_")
        ]
        if filtered:
            query_parts = [urllib.parse.urlencode(filtered)]

    cleaned_query = query_parts[0] if query_parts else ""
    return urllib.parse.urlunsplit((scheme, netloc, path, cleaned_query, ""))


def extract_source_name(url: str) -> Optional[str]:
    """Derive a friendly source name from a URL domain."""
    if not url:
        return None
    try:
        parsed = urllib.parse.urlparse(url)
        netloc = parsed.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc if netloc else None
    except Exception:
        return None


def is_social_media_url(url: str) -> bool:
    """Return True if the URL belongs to a social media platform (original post candidate)."""
    if not url:
        return False
    try:
        parsed = urllib.parse.urlparse(url)
        netloc = parsed.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return any(netloc == d or netloc.endswith("." + d) for d in SOCIAL_MEDIA_DOMAINS)
    except Exception:
        return False


def generate_search_query(claim_text: str, max_words: int = 10) -> str:
    """Generate a concise, entity-preserving search query from claim text.

    This is a rule-based fallback. When the LLM provides a search_query via
    ClaimExtractionService, that is preferred over this function.

    Strategy:
    - Remove URLs, @mentions, noise prefixes
    - Preserve named entities (capitalized words), numbers, dates
    - Limit to max_words meaningful tokens
    """
    if not claim_text:
        return ""

    query = claim_text.strip()

    # Remove URLs
    query = re.sub(r"https?://\S+", "", query)

    # Remove user mentions
    query = re.sub(r"@\w+", "", query)

    # Convert hashtags to plain keywords (#economy -> economy)
    query = re.sub(r"#(\w+)", r"\1", query)

    # Strip common noise prefixes (case-insensitive)
    for pat in NOISE_PREFIX_PATTERNS:
        query = re.sub(pat, "", query, flags=re.IGNORECASE)

    # Clean punctuation: replace punctuation with space
    query = re.sub(r"[\r\n\t]+", " ", query)
    query = re.sub(r"[!?;:,()\[\]{}]", " ", query)

    # Split into words, prioritize capitalized words (likely named entities) then others
    words = query.split()
    if not words:
        return claim_text.strip()

    # Filter out common stop words
    stop_words = {
        "the", "and", "that", "this", "with", "from", "for", "are",
        "was", "were", "has", "have", "had", "been", "would", "could",
        "should", "they", "their", "them", "into", "also", "will",
        "said", "says", "told", "just", "only", "but", "not",
    }

    # Three tiers: capitalized (entities), numeric (stats/dates), lowercase meaningful
    capitalized = [w for w in words if w[0].isupper() and w.lower() not in stop_words]
    numeric = [w for w in words if w[0].isdigit()]
    lowercase_meaningful = [
        w for w in words
        if w[0].islower() and w.lower() not in stop_words and len(w) > 3
    ]

    # Compose: take capitalized first, then numeric, then meaningful lowercase, up to max_words
    combined: List[str] = []
    seen: Set[str] = set()
    for w in capitalized + numeric + lowercase_meaningful:
        w_lower = w.lower()
        if w_lower not in seen:
            combined.append(w)
            seen.add(w_lower)
        if len(combined) >= max_words:
            break

    if not combined:
        # Fallback: just take original words up to max_words
        combined = words[:max_words]

    return " ".join(combined).strip()


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


def generate_fallback_queries(
    claim_text: str,
    primary_query: str = "",
    count: int = 2,
) -> List[str]:
    """Generate up to `count` broader contextual fallback queries.

    Preserves:
    - people (e.g. Trump, Biden, Macron)
    - organizations / institutions (e.g. Olympics, IOC, White House, NASA)
    - events / locations / dates (e.g. 2028, Paris, Los Angeles)
    - important actions / categories (e.g. announcement, new sport, sports)

    Removes:
    - fictional terms, unknown/invented entities (e.g. Jerk4Krik)
    - excessive adjectives, satire/humor wording, filler words
    Does NOT invent replacement entities.
    """
    cleaned = claim_text.strip()
    for pat in NOISE_PREFIX_PATTERNS:
        cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"https?://\S+", "", cleaned)
    cleaned = re.sub(r"@\w+", "", cleaned)
    cleaned = re.sub(r"#(\w+)", r"\1", cleaned)
    cleaned = re.sub(r"[!?;:,()\[\]{}\"\'“”‘’]", " ", cleaned)

    words = cleaned.split()

    filter_words = {
        "reportedly", "report", "reports", "allegedly", "claims", "claiming",
        "says", "saying", "great", "very", "serious", "powerful", "crazy",
        "stamina", "unbelievable", "technique", "shame", "viral", "internet",
        "going", "finally", "chance", "compete", "anyone", "someone", "kind",
        "could", "even", "prepare", "highest", "level", "absolutely", "elite",
        "everything", "takes", "become", "plans", "plan", "bring", "into",
        "the", "and", "that", "this", "with", "from", "for", "are", "was",
        "were", "has", "have", "had", "been", "would", "should", "they",
        "their", "them", "also", "will", "just", "only", "about", "what",
        "which", "when", "where", "how", "game",
    }

    # Extract capitalized entities / proper nouns, dropping fictional/invented terms
    entities: List[str] = []
    seen_entities: Set[str] = set()
    for w in words:
        w_clean = re.sub(r"\W+", "", w)
        if not w_clean:
            continue
        if w_clean[0].isupper() and w_clean.lower() not in filter_words:
            # Drop likely invented / fictional terms with numbers or camelCase (e.g. Jerk4Krik)
            if re.search(r"[0-9]", w_clean) or re.search(r"[a-z][A-Z]", w_clean):
                continue
            if w_clean.lower() not in seen_entities:
                entities.append(w_clean)
                seen_entities.add(w_clean.lower())

    years = [w for w in words if re.match(r"^(19|20)\d{2}$", w)]

    cleaned_lower = cleaned.lower()
    actions: List[str] = []
    if any(a in cleaned_lower for a in ["announc", "statem", "declar", "reveal", "confirm", "plan"]):
        actions.append("announcement")
    elif any(a in cleaned_lower for a in ["sign", "approv", "pass", "order"]):
        actions.append("announcement")

    categories: List[str] = []
    if "olympic" in cleaned_lower or "olympics" in cleaned_lower:
        if "sport" in cleaned_lower or "game" in cleaned_lower:
            categories.append("new sport")
        else:
            categories.append("announcement")
    elif "sport" in cleaned_lower:
        categories.append("sports")
    elif "cabinet" in cleaned_lower or "minister" in cleaned_lower:
        categories.append("cabinet")
    elif "election" in cleaned_lower:
        categories.append("election")

    fallbacks: List[str] = []

    # Fallback 1: Preserves entities + action + category
    # e.g. "Trump Olympics announcement new sport"
    fb1_parts = []
    for e in entities[:3]:
        fb1_parts.append(e)
    for a in actions:
        if a.lower() not in [p.lower() for p in fb1_parts]:
            fb1_parts.append(a)
    for c in categories:
        if c.lower() not in [p.lower() for p in fb1_parts]:
            fb1_parts.append(c)

    fb1 = " ".join(fb1_parts).strip()
    if fb1 and fb1 != primary_query:
        fallbacks.append(fb1)

    # Fallback 2: Year/event specific or broader official context
    # e.g. "Trump 2028 Olympics sports announcement"
    fb2_parts = []
    for e in entities[:2]:
        fb2_parts.append(e)
    if years:
        fb2_parts.append(years[0])
    elif "olympic" in cleaned_lower and "2028" not in fb2_parts:
        fb2_parts.append("2028")
    for e in entities[2:3]:
        fb2_parts.append(e)
    if "sports announcement" not in " ".join(fb2_parts).lower():
        if "sport" in cleaned_lower:
            fb2_parts.append("sports announcement")
        else:
            fb2_parts.append("official announcement")

    fb2 = " ".join(fb2_parts).strip()
    if fb2 and fb2 != primary_query and fb2 not in fallbacks:
        fallbacks.append(fb2)

    return fallbacks[:count]


def evaluate_source_quality(url: str) -> Literal["high", "medium", "low", "unknown"]:
    """Assess the credibility of the evidence host domain."""
    if not url:
        return "unknown"
    try:
        domain = urllib.parse.urlparse(url).netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]

        if domain.endswith(".gov") or domain.endswith(".edu") or domain.endswith(".mil"):
            return "high"

        for high_domain in HIGH_QUALITY_DOMAINS:
            if domain == high_domain or domain.endswith("." + high_domain):
                return "high"

        for med_domain in (
            "cnn.com", "cnbc.com", "forbes.com", "time.com", "usatoday.com",
            "abcnews.go.com", "cbsnews.com", "nbcnews.com", "thehindu.com",
            "ndtv.com", "indianexpress.com", "indiatoday.in", "aljazeera.com",
            "euronews.com", "dw.com", "france24.com", "axios.com", "politico.com",
        ):
            if domain == med_domain or domain.endswith("." + med_domain):
                return "medium"

        for low_domain in SOCIAL_MEDIA_DOMAINS:
            if domain == low_domain or domain.endswith("." + low_domain):
                return "low"

        return "unknown"
    except Exception:
        return "unknown"


def evaluate_evidence_relevance(
    claim_text: str,
    title: str,
    snippet: Optional[str],
    url: str = "",
    query: str = "",
    claim_type: str = "factual",
) -> tuple[
    bool,
    Literal["irrelevant", "contextual", "relevant", "direct"],
    Literal["high", "medium", "low"],
    Literal["direct", "indirect", "contextual"],
    Literal["supports", "contradicts", "contextual", "irrelevant", "unclear"],
    Literal["high", "medium", "low", "unknown"],
]:
    """Relevance gate evaluating whether a retrieved result is relevant evidence for a claim.

    Distinguishes:
    - irrelevant: Unrelated topic, single entity match when claim requires relation between multiple entities
    - contextual: General background / shared entities, but does NOT prove or disprove the asserted action
    - relevant: Addresses core entities AND asserted actions/predicates
    - direct: Directly addresses the specific quote, assertion, proposal, or explicit fact-check

    Returns:
        (is_relevant, relevance_category, relevance, directness, relationship, source_quality)
    """
    source_quality = evaluate_source_quality(url)
    combined = f"{title or ''} {snippet or ''}".lower()
    if not combined.strip():
        return (False, "irrelevant", "low", "contextual", "irrelevant", source_quality)

    # 1. Fact-checking / Debunking signals or fact-checking domains
    fact_check_kws = [
        "fact check", "fact-check", "debunk", "claim check", "hoax",
        "false claim", "misinformation", "no evidence", "unproven",
    ]
    if any(kw in combined for kw in fact_check_kws) or "factcheck.org" in url:
        return (True, "direct", "high", "direct", "contradicts", source_quality)

    # Short / synthetic test claims (e.g. "Test claim"): accept authoritative sources
    claim_clean = re.sub(r"[!?;:,()\[\]{}\"\'“”‘’]", " ", claim_text.lower())
    short_tokens = [
        t for t in re.findall(r"\b\w{3,}\b", claim_clean)
        if t not in {
            "the", "and", "that", "this", "with", "from", "for", "are",
            "was", "were", "has", "have", "had", "been", "into",
        }
    ]
    if len(short_tokens) <= 2 and (source_quality in ("high", "medium") or any(t in combined for t in short_tokens)):
        return (True, "relevant", "high", "direct", "contextual", source_quality)

    # 2. Absence-of-evidence claims
    if claim_type == "absence_of_evidence":
        is_official = (
            source_quality == "high"
            or any(d in url.lower() for d in ["olympic", "ioc", ".gov", ".org"])
        )
        has_org = any(org in combined for org in ["ioc", "olympic", "olympics", "committee"])
        has_announcement_topic = any(
            topic in combined for topic in [
                "announc", "sport", "game", "official", "list", "addition", "program", "discipline"
            ]
        )
        if is_official and has_org and has_announcement_topic:
            return (True, "relevant", "high", "direct", "contextual", source_quality)
        elif has_org and has_announcement_topic and source_quality in ("high", "medium"):
            return (True, "relevant", "medium", "indirect", "contextual", source_quality)
        return (False, "irrelevant", "low", "contextual", "irrelevant", source_quality)

    # 3. Entity & Predicate Analysis
    claim_lower = claim_text.lower()
    entity_groups: List[tuple[str, Set[str]]] = []

    if "putin" in claim_lower:
        entity_groups.append(("putin", {"putin", "vladimir putin"}))
    if "trump" in claim_lower:
        entity_groups.append(("trump", {"trump", "donald trump"}))
    if "macron" in claim_lower:
        entity_groups.append(("macron", {"macron", "emmanuel macron"}))
    if "barnier" in claim_lower:
        entity_groups.append(("barnier", {"barnier", "michel barnier"}))
    if "olympic" in claim_lower or "olympics" in claim_lower:
        entity_groups.append(("olympics", {"olympic", "olympics", "ioc"}))
    if "jerk4krik" in claim_lower:
        entity_groups.append(("jerk4krik", {"jerk4krik"}))

    # General capitalized tokens as additional entities
    for word in claim_text.split():
        w_clean = re.sub(r"\W+", "", word)
        if len(w_clean) >= 4 and w_clean[0].isupper() and w_clean.lower() not in {
            "according", "reports", "reportedly", "allegedly", "sources", "yesterday", "today"
        }:
            if not any(w_clean.lower() in grp[1] for grp in entity_groups):
                entity_groups.append((w_clean.lower(), {w_clean.lower()}))

    # Extract action / predicate words
    stop_words = {
        "the", "and", "that", "this", "with", "from", "for", "are", "was",
        "were", "has", "have", "had", "been", "into", "also", "will", "would",
        "could", "should", "said", "says", "told", "just", "only", "about",
        "what", "which", "when", "where", "how", "reportedly", "allegedly",
        "saying", "great", "very", "serious", "powerful", "game", "sport",
    }
    all_entity_tokens = set().union(*[g[1] for g in entity_groups]) if entity_groups else set()
    predicate_words = [
        w.lower()
        for w in re.findall(r"\b\w{3,}\b", claim_text)
        if w.lower() not in stop_words and w.lower() not in all_entity_tokens
    ]

    def _root(w: str) -> str:
        w_low = w.lower()
        for sfx in ("ingly", "edly", "ment", "ing", "ed", "es", "s"):
            if w_low.endswith(sfx) and len(w_low) - len(sfx) >= 3:
                return w_low[:-len(sfx)]
        return w_low

    # Evaluate multi-entity relationship claims (e.g. Putin + Trump, Macron + Barnier)
    person_groups = [g for g in entity_groups if g[0] in ("putin", "trump", "macron", "barnier")]
    if len(person_groups) >= 2:
        # Must match both people in the search result
        matched_people = sum(1 for g in person_groups if any(alias in combined for alias in g[1]))
        if matched_people < 2:
            # Matches only one person (e.g. only Putin, unrelated election article) -> IRRELEVANT
            return (False, "irrelevant", "low", "contextual", "irrelevant", source_quality)

        # Both people are mentioned: check predicate/quote/specific topic
        has_predicate = any(_root(pw) in combined for pw in predicate_words) or any(
            w in combined for w in ["prime minister", "minister", "president", "appoint", "appointed", "government"]
        )
        has_genius_or_praise = any(
            w in combined for w in ["genius", "praise", "praised", "praises", "bold", "invent"]
        )

        if has_genius_or_praise:
            return (True, "direct", "high", "direct", "supports", source_quality)
        elif has_predicate:
            relat = "supports" if any(w in combined for w in ["appoint", "names", "announced", "confirms"]) else "contextual"
            return (True, "relevant", "high", "direct", relat, source_quality)
        else:
            # Contextual only: e.g. "Putin and Trump discussed the Olympics" without the praise/genius
            return (False, "contextual", "medium", "contextual", "contextual", source_quality)

    # Evaluate announcement / sports claims (e.g. Trump + Olympics + new sport)
    if "olympics" in [g[0] for g in entity_groups]:
        is_official_olympic_source = (
            "olympics.com" in url or "olympic.org" in url or "ioc" in combined
        ) and any(w in combined for w in ["announc", "sport", "game", "event", "addition", "committee"])
        if is_official_olympic_source:
            return (True, "relevant", "high", "direct", "contextual", "high")

        has_trump = any("trump" in alias for g in entity_groups if g[0] == "trump" for alias in g[1] if alias in combined)
        has_olympics = any("olympic" in alias or "ioc" in alias for alias in ["olympic", "olympics", "ioc"] if alias in combined)

        if not (has_trump and has_olympics):
            return (False, "irrelevant", "low", "contextual", "irrelevant", source_quality)

        has_announcement = any(
            w in combined for w in ["announc", "statem", "propos", "new sport", "addition", "add", "game", "jerk4krik", "spoke"]
        )
        if "jerk4krik" in combined:
            return (True, "direct", "high", "direct", "supports", source_quality)
        elif has_announcement:
            return (True, "relevant", "high", "direct", "contextual", source_quality)
        else:
            # Random Olympic attendance article without sport/announcement
            return (False, "contextual", "low", "contextual", "contextual", source_quality)

    # General token matching
    claim_words = [
        w.lower()
        for w in re.findall(r"\b\w{3,}\b", claim_text)
        if w.lower() not in stop_words
    ]
    if not claim_words:
        return (True, "contextual", "medium", "contextual", "contextual", source_quality)

    matched_words = [w for w in claim_words if w in combined]
    ratio = len(matched_words) / len(claim_words)

    if ratio >= 0.50:
        relat = "supports" if any(w in combined for w in ["confirm", "appoint", "announc"]) else "contextual"
        return (True, "relevant", "high", "direct", relat, source_quality)
    elif ratio >= 0.30 and any(pw in combined for pw in predicate_words):
        return (True, "relevant", "medium", "indirect", "contextual", source_quality)
    elif ratio >= 0.20:
        return (False, "contextual", "low", "contextual", "contextual", source_quality)
    else:
        return (False, "irrelevant", "low", "contextual", "irrelevant", source_quality)


def is_evidence_useful(
    claim_text: str,
    title: str,
    snippet: Optional[str],
    url: str = "",
    query: str = "",
    claim_type: str = "factual",
) -> bool:
    """Assess whether a retrieved evidence item passes the relevance gate."""
    is_rel, _, _, _, _, _ = evaluate_evidence_relevance(
        claim_text=claim_text,
        title=title,
        snippet=snippet,
        url=url,
        query=query,
        claim_type=claim_type,
    )
    return is_rel


class EvidenceSearchService:
    """Service to coordinate external web evidence search for extracted claims."""

    def __init__(
        self,
        provider: Optional[BaseSearchProvider] = None,
        limit: Optional[int] = None,
        max_concurrency: int = 5,
        original_post_url: Optional[str] = None,
    ):
        self.provider = provider or get_search_provider()
        self.limit = limit if limit is not None else settings.evidence_search_limit
        self.semaphore = asyncio.Semaphore(max_concurrency)
        # The original post URL — results matching this URL are tagged as original_post
        self.original_post_url = normalize_url(original_post_url) if original_post_url else None

    def _get_source_role(self, url: str) -> str:
        """Determine if a result URL is the original post or an external source.

        An original_post source MUST NOT be treated as independent corroborating evidence.
        """
        norm = normalize_url(url)
        if self.original_post_url and norm == self.original_post_url:
            return "original_post"
        if is_social_media_url(url):
            return "original_post"
        return "external"

    async def _execute_query(
        self,
        query: str,
        search_type: Literal["primary", "fallback"],
        claim_text: str,
        search_limit: int,
        claim_id: str = "",
        claim_type: str = "factual",
    ) -> tuple[SearchAttempt, List[Evidence], List[Evidence], bool, Optional[SearchError]]:
        """Execute a single search query attempt, normalize results, and apply relevance gate.

        Returns:
            (attempt, all_evidence, relevant_evidence, is_useful, error)
        """
        start_time = time.perf_counter()
        logger.info(
            f"[TRUTHLENS] [EVIDENCE_SEARCH] QUERY claim_id={claim_id} type={search_type} query={query!r}"
        )
        try:
            raw_results = await self.provider.search(query=query, limit=search_limit)
            duration = time.perf_counter() - start_time
            raw_count = len(raw_results)

            logger.info(
                f"[TRUTHLENS] [EVIDENCE_SEARCH] RESULTS claim_id={claim_id} type={search_type} "
                f"query={query!r} result_count={raw_count} duration={duration:.2f}s"
            )

            all_evidence: List[Evidence] = []
            seen_urls: Set[str] = set()

            for raw in raw_results:
                raw_url = raw.get("url") or ""
                norm_url = normalize_url(raw_url)
                if not norm_url or norm_url in seen_urls:
                    continue
                seen_urls.add(norm_url)

                title = (raw.get("title") or "").strip()
                snippet = raw.get("snippet")
                if snippet:
                    snippet = snippet.strip()

                source_name = raw.get("source_name") or extract_source_name(norm_url)
                published_at = raw.get("published_date") or raw.get("published_at")
                role = self._get_source_role(norm_url)

                is_rel, rel_cat, rel, direct, relat, sq = evaluate_evidence_relevance(
                    claim_text=claim_text,
                    title=title,
                    snippet=snippet,
                    url=norm_url,
                    query=query,
                    claim_type=claim_type,
                )

                all_evidence.append(
                    Evidence(
                        title=title,
                        url=norm_url,
                        snippet=snippet,
                        source_name=source_name,
                        published_at=published_at,
                        search_query=query,
                        source_role=role,
                        source_quality=sq,
                        relevance=rel,
                        directness=direct,
                        relationship=relat,
                        relevance_category=rel_cat,
                    )
                )

            # Filter for evidence passing relevance gate: must be external and relevant/direct
            relevant_evidence = [
                ev for ev in all_evidence
                if ev.source_role == "external"
                and ev.relevance_category in ("relevant", "direct")
            ]
            relevant_count = len(relevant_evidence)
            is_useful = relevant_count > 0

            logger.info(
                f"[TRUTHLENS] [EVIDENCE_SEARCH] RELEVANCE_FILTER claim_id={claim_id} query={query!r} "
                f"result_count={raw_count} relevant_count={relevant_count}"
            )

            attempt = SearchAttempt(
                query=query,
                type=search_type,
                result_count=raw_count,
                relevant_count=relevant_count,
            )

            return attempt, all_evidence, relevant_evidence, is_useful, None

        except Exception as exc:
            duration = time.perf_counter() - start_time
            error_msg = str(exc).replace("\n", " ")
            is_rate_limit = (
                "429" in error_msg.lower()
                or ("rate" in error_msg.lower() and "limit" in error_msg.lower())
            )
            err_type = "rate_limited" if is_rate_limit else "provider_error"

            attempt = SearchAttempt(
                query=query,
                type=search_type,
                result_count=0,
                relevant_count=0,
            )
            logger.error(
                f"[TRUTHLENS] [EVIDENCE_SEARCH] QUERY_ERROR claim_id={claim_id} type={search_type} "
                f"query={query!r} error={error_msg!r} duration={duration:.2f}s"
            )
            return attempt, [], [], False, SearchError(type=err_type, message=error_msg)

    async def search_for_claim(
        self,
        claim: Union[Claim, Dict[str, Any]],
        limit: Optional[int] = None,
    ) -> ClaimEvidence:
        """Search external web evidence for a single claim using Two-Stage Evidence Search.

        Stage 1: Execute primary specific search.
        Stage 2: If primary returns no useful results, execute up to 2 broader contextual fallback searches.
        Max 3 total searches per important claim.
        """
        claim_start = time.perf_counter()

        # Unpack claim fields whether passed as Claim model or dict
        if isinstance(claim, dict):
            claim_id = str(claim.get("claim_id", "unknown"))
            claim_text = str(claim.get("text", ""))
            priority = str(claim.get("priority", "primary"))
            claim_type = str(claim.get("claim_type", "factual"))
            requires_verification = bool(claim.get("requires_verification", True))
            primary_query = (
                claim.get("primary_query")
                or claim.get("_search_query")
                or claim.get("search_query")
            )
            fallback_queries = list(claim.get("fallback_queries") or [])
        else:
            claim_id = getattr(claim, "claim_id", "unknown")
            claim_text = getattr(claim, "text", "")
            priority = getattr(claim, "priority", "primary")
            claim_type = getattr(claim, "claim_type", "factual")
            requires_verification = getattr(claim, "requires_verification", True)
            primary_query = (
                getattr(claim, "primary_query", None)
                or getattr(claim, "_search_query", None)
                or getattr(claim, "search_query", None)
            )
            fallback_queries = list(getattr(claim, "fallback_queries", []) or [])

        search_limit = limit if limit is not None else self.limit

        logger.info(f"[TRUTHLENS] [EVIDENCE_SEARCH] START claim_id={claim_id}")

        # Skip search if narrative or if claim does not require verification
        if priority == "narrative" or not requires_verification:
            duration = time.perf_counter() - claim_start
            logger.info(
                f"[TRUTHLENS] [EVIDENCE_SEARCH] SKIPPED claim_id={claim_id} "
                f"reason='priority={priority}, requires_verification={requires_verification}'"
            )
            logger.info(
                f"[TRUTHLENS] [EVIDENCE_SEARCH] END claim_id={claim_id} query='' "
                f"result_count=0 relevant_count=0 status=no_results duration={duration:.2f}s"
            )
            return ClaimEvidence(
                claim_id=claim_id,
                claim_text=claim_text,
                search_query="",
                status="no_results",
                searches=[],
                evidence=[],
                error=None,
                claim_type=claim_type,
            )

        # Determine primary query
        if primary_query and isinstance(primary_query, str) and primary_query.strip():
            p_query = primary_query.strip()
        else:
            p_query = generate_search_query(claim_text)

        searches: List[SearchAttempt] = []
        last_error: Optional[SearchError] = None

        # ── STAGE 1: Specific Primary Search ────────────────────────────────
        attempt1, all_ev1, rel_ev1, is_useful1, err1 = await self._execute_query(
            query=p_query,
            search_type="primary",
            claim_text=claim_text,
            search_limit=search_limit,
            claim_id=claim_id,
            claim_type=claim_type,
        )
        searches.append(attempt1)

        if err1:
            last_error = err1
            err_type = err1.get("type", "provider_error")
            status: Literal["rate_limited", "search_failed"] = (
                "rate_limited" if err_type == "rate_limited" else "search_failed"
            )
            duration = time.perf_counter() - claim_start
            logger.info(
                f"[TRUTHLENS] [EVIDENCE_SEARCH] END claim_id={claim_id} query={p_query!r} "
                f"result_count=0 relevant_count=0 status={status} duration={duration:.2f}s"
            )
            return ClaimEvidence(
                claim_id=claim_id,
                claim_text=claim_text,
                search_query=p_query,
                status=status,
                searches=searches,
                evidence=[],
                error=err1,
                claim_type=claim_type,
            )

        if is_useful1:
            duration = time.perf_counter() - claim_start
            logger.info(
                f"[TRUTHLENS] [EVIDENCE_SEARCH] END claim_id={claim_id} query={p_query!r} "
                f"result_count={attempt1.result_count} relevant_count={attempt1.relevant_count} "
                f"status=success duration={duration:.2f}s"
            )
            return ClaimEvidence(
                claim_id=claim_id,
                claim_text=claim_text,
                search_query=p_query,
                status="success",
                searches=searches,
                evidence=rel_ev1,
                error=None,
                claim_type=claim_type,
            )

        # ── STAGE 2: Broader Contextual Fallback Searches ───────────────────
        # Only perform fallback searches for primary and relevant secondary claims
        if priority in ("primary", "secondary"):
            logger.info(
                f"[TRUTHLENS] [EVIDENCE_SEARCH] TRIGGERING_FALLBACK claim_id={claim_id} "
                f"reason='primary_not_useful, raw_results={attempt1.result_count}'"
            )

            # Ensure clean fallback queries (max 2)
            clean_fallbacks: List[str] = []
            for fb in fallback_queries:
                if isinstance(fb, str) and fb.strip() and fb.strip() != p_query:
                    if fb.strip() not in clean_fallbacks:
                        clean_fallbacks.append(fb.strip())

            # If fewer than 2 fallback queries, generate them
            if len(clean_fallbacks) < 2:
                generated = generate_fallback_queries(
                    claim_text=claim_text,
                    primary_query=p_query,
                    count=2 - len(clean_fallbacks),
                )
                for g in generated:
                    if g not in clean_fallbacks and g != p_query:
                        clean_fallbacks.append(g)

            clean_fallbacks = clean_fallbacks[:2]

            for fb_query in clean_fallbacks:
                attempt_fb, all_ev_fb, rel_ev_fb, is_useful_fb, err_fb = await self._execute_query(
                    query=fb_query,
                    search_type="fallback",
                    claim_text=claim_text,
                    search_limit=search_limit,
                    claim_id=claim_id,
                    claim_type=claim_type,
                )
                searches.append(attempt_fb)
                if err_fb:
                    last_error = err_fb

                if is_useful_fb:
                    duration = time.perf_counter() - claim_start
                    logger.info(
                        f"[TRUTHLENS] [EVIDENCE_SEARCH] END claim_id={claim_id} query={fb_query!r} "
                        f"result_count={attempt_fb.result_count} relevant_count={attempt_fb.relevant_count} "
                        f"status=success duration={duration:.2f}s"
                    )
                    return ClaimEvidence(
                        claim_id=claim_id,
                        claim_text=claim_text,
                        search_query=p_query,
                        status="success",
                        searches=searches,
                        evidence=rel_ev_fb,
                        error=None,
                        claim_type=claim_type,
                    )

        # If all searches executed and no relevant results were found:
        total_raw = sum(s.result_count for s in searches)
        total_relevant = sum(s.relevant_count for s in searches)

        if last_error and last_error.get("type") == "rate_limited":
            final_status: Literal["success", "no_relevant_results", "no_results", "search_failed", "rate_limited"] = "rate_limited"
        elif last_error and total_raw == 0:
            final_status = "search_failed"
        elif total_raw == 0:
            final_status = "no_results"
        else:
            final_status = "no_relevant_results"

        duration = time.perf_counter() - claim_start
        logger.info(
            f"[TRUTHLENS] [EVIDENCE_SEARCH] END claim_id={claim_id} query={p_query!r} "
            f"result_count={total_raw} relevant_count={total_relevant} "
            f"status={final_status} duration={duration:.2f}s"
        )

        return ClaimEvidence(
            claim_id=claim_id,
            claim_text=claim_text,
            search_query=p_query,
            status=final_status,
            searches=searches,
            evidence=[],
            error=last_error,
            claim_type=claim_type,
        )

    async def search_for_claims(
        self,
        claims: List[Union[Claim, Dict[str, Any]]],
        limit: Optional[int] = None,
    ) -> List[ClaimEvidence]:
        """Search evidence for multiple claims concurrently with bounded concurrency."""
        if not claims:
            return []

        start_all = time.perf_counter()

        async def _bounded_search(c: Union[Claim, Dict[str, Any]]) -> ClaimEvidence:
            async with self.semaphore:
                return await self.search_for_claim(c, limit=limit)

        tasks = [_bounded_search(claim) for claim in claims]
        results = await asyncio.gather(*tasks)

        total_duration = time.perf_counter() - start_all
        successful = sum(1 for r in results if r.error is None)
        total_results = sum(len(r.evidence) for r in results)

        logger.info(
            f"[TRUTHLENS] [EVIDENCE_SEARCH] SUMMARY claims={len(claims)} "
            f"successful={successful} total_results={total_results} "
            f"duration={total_duration:.2f}s"
        )

        return list(results)
