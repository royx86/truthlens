"""
Facebook platform scraper and normalizer.

Responsibilities:
  1. Validate that the URL is a supported Facebook URL (page, post, video, reel).
  2. Build Actor input conforming to apify/facebook-posts-scraper schema.
  3. Delegate scraping to ApifyService.
  4. Select the matching item if multiple results are returned.
  5. Store raw Apify data internally in ScrapeResult.
  6. Normalise the raw Apify Actor response into a universal NormalizedPost.
"""

from datetime import datetime, timezone
import logging
import re
from typing import Any
from urllib.parse import parse_qs, urlparse

from app.core.config import get_settings
from app.platforms.base import BasePlatformScraper
from app.schemas.post import Author, Media, NormalizedPost, ScrapeResult
from app.services.apify_service import ApifyService

logger = logging.getLogger(__name__)

# Configurable results limit for Actor runs
# Default: 5 posts per request (keeps runs fast and prevents excessive scraping)
DEFAULT_RESULTS_LIMIT = 5

# Recognized Facebook domain hosts (without leading www.)
_VALID_HOSTS = {
    "facebook.com",
    "fb.com",
    "fb.watch",
    "m.facebook.com",
    "web.facebook.com",
}

# Facebook internal/system paths that cannot be scraped as user/page content
_SYSTEM_PATHS = {
    "",
    "/",
    "/login",
    "/login.php",
    "/recover",
    "/recover.php",
    "/settings",
    "/help",
    "/policies",
    "/terms",
    "/privacy",
    "/checkpoint",
    "/messages",
    "/notifications",
}


def validate_facebook_url(url: str) -> None:
    """
    Raise ValueError if the URL is not a valid, supported public Facebook URL.

    Accepts:
      - Page URLs (e.g. https://www.facebook.com/example)
      - Post URLs (e.g. https://www.facebook.com/example/posts/123456)
      - Video / Watch URLs (e.g. https://fb.watch/abc123/, https://www.facebook.com/watch/?v=123)
      - Reel URLs (e.g. https://www.facebook.com/reel/123456)
      - Photo URLs (e.g. https://www.facebook.com/photo/?fbid=123456)
      - Permalink/Story URLs (e.g. https://www.facebook.com/permalink.php?story_fbid=123&id=456)

    Rejects:
      - Empty strings or malformed URLs
      - Non-Facebook hosts
      - Root paths without identifiers (e.g. https://www.facebook.com/)
      - Internal/System pages (e.g. /login, /recover, /settings, /policies)
    """
    url = url.strip()
    if not url:
        raise ValueError("Facebook URL cannot be empty.")

    # Ensure scheme for urlparse
    if "://" not in url:
        url = "https://" + url

    try:
        parsed = urlparse(url)
    except Exception as exc:
        raise ValueError(f"Malformed Facebook URL: {exc}") from exc

    hostname = (parsed.hostname or "").lower()
    if hostname.startswith("www."):
        hostname = hostname[4:]

    if hostname not in _VALID_HOSTS:
        raise ValueError(
            f"Host '{hostname}' is not a recognized Facebook domain."
        )

    path = parsed.path.rstrip("/")
    query = parse_qs(parsed.query)

    # Root domain check (e.g. https://www.facebook.com or https://fb.com)
    if not path or path == "":
        has_identifying_query = bool(
            query.get("id") or query.get("story_fbid") or query.get("v") or query.get("fbid")
        )
        if not has_identifying_query:
            raise ValueError(
                "Invalid Facebook URL: Please provide a specific post, video, reel, or page URL "
                "(e.g., https://www.facebook.com/pagename or https://www.facebook.com/pagename/posts/123)."
            )

    # Check for system / auth paths
    if path.lower() in _SYSTEM_PATHS:
        has_identifying_query = bool(
            query.get("id") or query.get("story_fbid") or query.get("v") or query.get("fbid")
        )
        if not has_identifying_query:
            raise ValueError(
                f"Invalid Facebook URL: '{path}' is a system page and cannot be scraped."
            )


def _build_actor_input(url: str, results_limit: int = DEFAULT_RESULTS_LIMIT) -> dict[str, Any]:
    """
    Build the run_input dict for apify/facebook-posts-scraper.

    The official Apify Actor expects:
    {
      "startUrls": [{"url": "<FACEBOOK_URL>"}],
      "resultsLimit": 5
    }
    """
    return {
        "startUrls": [{"url": url}],
        "resultsLimit": results_limit,
    }


def _clean_url_for_matching(url: str) -> str:
    """Normalize a URL for loose matching by stripping scheme, www, and trailing slashes."""
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        if host.startswith("www."):
            host = host[4:]
        path = parsed.path.rstrip("/")
        return f"{host}{path}"
    except Exception:
        return url.strip().rstrip("/")


def _extract_post_id(url: str) -> str | None:
    """Attempt to extract an identifier (postId, reelId, fbid) from a Facebook URL."""
    patterns = [
        r"/posts/([A-Za-z0-9_\-]+)",
        r"/reel/([A-Za-z0-9_\-]+)",
        r"/videos/([0-9]+)",
        r"[?&]story_fbid=([0-9]+)",
        r"[?&]fbid=([0-9]+)",
        r"[?&]v=([0-9]+)",
    ]
    for pat in patterns:
        m = re.search(pat, url)
        if m:
            return m.group(1)
    return None


def _select_best_item(items: list[dict[str, Any]], requested_url: str) -> dict[str, Any]:
    """
    Select the result corresponding to the requested URL where possible.

    If exact matching is not possible, returns the first available result
    data rather than inventing a match.
    """
    if not items:
        return {}
    if len(items) == 1:
        return items[0]

    clean_requested = _clean_url_for_matching(requested_url)
    post_id = _extract_post_id(requested_url)

    for item in items:
        if not isinstance(item, dict):
            continue

        item_url = item.get("url")
        if item_url and _clean_url_for_matching(item_url) == clean_requested:
            return item

        item_top_url = item.get("topLevelUrl")
        if item_top_url and _clean_url_for_matching(item_top_url) == clean_requested:
            return item

        if post_id:
            item_post_id = str(item.get("postId") or "")
            if item_post_id and item_post_id == post_id:
                return item
            if item_url and post_id in item_url:
                return item
            if item_top_url and post_id in item_top_url:
                return item

    # If exact matching is not possible, return the available result data
    return items[0]


def normalize_facebook_post(raw: dict[str, Any], original_url: str) -> NormalizedPost:
    """
    Pure normalizer function converting raw Apify Facebook JSON into universal NormalizedPost.

    Extracts:
      - text from text / postText / caption
      - published_at from time / timestamp
      - author into universal Author model
      - media (images, attachments, videos, reels, dimensions, ocrText) into universal Media
      - external_links from textReferences, link, or text
      - engagement & platform identifiers into metadata
    """
    # ── Text ─────────────────────────────────────────────────────────────────
    text_val = raw.get("text") or raw.get("postText") or raw.get("caption") or raw.get("message")
    text = str(text_val) if text_val is not None else None

    # ── Timestamps ───────────────────────────────────────────────────────────
    time_val = raw.get("time")
    if time_val and isinstance(time_val, str):
        published_at = time_val
    else:
        ts = raw.get("timestamp") or raw.get("timestampCreated") or raw.get("timeCreated")
        if isinstance(ts, (int, float)):
            published_at = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
        elif ts:
            published_at = str(ts)
        else:
            published_at = None

    # ── Author ───────────────────────────────────────────────────────────────
    user_obj = raw.get("user")
    if isinstance(user_obj, dict):
        author_id = str(user_obj.get("id") or "") or str(raw.get("facebookId") or "") or None
        author_name = user_obj.get("name") or raw.get("pageName")
        profile_pic = user_obj.get("profilePic") or user_obj.get("profilePicture")
        profile_url = user_obj.get("profileUrl") or raw.get("facebookUrl")
        username = user_obj.get("username")  # None if unavailable, no fabrication
    else:
        author_id = str(raw.get("facebookId") or "") or None
        author_name = raw.get("pageName") or raw.get("author") or (user_obj if isinstance(user_obj, str) else None)
        profile_pic = None
        profile_url = raw.get("facebookUrl") or (f"https://www.facebook.com/{raw['pageName']}" if raw.get("pageName") else None)
        username = None

    author: Author | None = None
    if author_name or author_id or profile_url or profile_pic or username:
        author = Author(
            id=author_id,
            name=author_name,
            username=username,
            profile_url=profile_url,
            profile_image_url=profile_pic,
        )

    # ── Media ────────────────────────────────────────────────────────────────
    media_items: list[Media] = []
    seen_media: set[tuple[str, str | None]] = set()

    # Collect both 'media' and 'attachments' from raw Facebook response
    raw_media_candidates: list[Any] = []
    if isinstance(raw.get("media"), list):
        raw_media_candidates.extend(raw["media"])
    if isinstance(raw.get("attachments"), list):
        raw_media_candidates.extend(raw["attachments"])

    for item in raw_media_candidates:
        if isinstance(item, dict):
            # Check if video
            is_video = (
                item.get("__typename") == "Video"
                or item.get("__isMedia") == "Video"
                or bool(item.get("video_url") or item.get("videoUrl"))
                or item.get("is_playable") is True
            )
            if is_video:
                v_url = item.get("video_url") or item.get("videoUrl") or item.get("url")
                v_thumb = item.get("thumbnail") or item.get("thumbnailUrl") or item.get("video_thumbnail_url")
                w_val = item.get("width")
                h_val = item.get("height")
                w = int(w_val) if isinstance(w_val, (int, float)) else None
                h = int(h_val) if isinstance(h_val, (int, float)) else None
                v_meta: dict[str, Any] = {}
                if item.get("video_duration_seconds") is not None:
                    v_meta["duration"] = item["video_duration_seconds"]

                if (v_url or v_thumb) and ("video", v_url) not in seen_media:
                    seen_media.add(("video", v_url))
                    media_items.append(
                        Media(
                            type="video",
                            url=v_url,
                            thumbnail_url=v_thumb,
                            width=w,
                            height=h,
                            ocr_text=None,
                            metadata=v_meta,
                        )
                    )
            else:
                # Photo / Image
                photo_image = item.get("photo_image") or item.get("image")
                p_url = None
                w = None
                h = None
                if isinstance(photo_image, dict):
                    p_url = photo_image.get("uri") or photo_image.get("url")
                    w_raw = photo_image.get("width")
                    h_raw = photo_image.get("height")
                    w = int(w_raw) if isinstance(w_raw, (int, float)) else None
                    h = int(h_raw) if isinstance(h_raw, (int, float)) else None

                thumb = item.get("thumbnail") or item.get("thumbnailUrl")
                if not p_url:
                    item_url = item.get("url")
                    if thumb:
                        p_url = thumb
                    elif item_url and ("fbcdn.net" in item_url or any(item_url.lower().endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".webp"))):
                        p_url = item_url
                if not thumb:
                    thumb = p_url

                if w is None and isinstance(item.get("width"), (int, float)):
                    w = int(item["width"])
                if h is None and isinstance(item.get("height"), (int, float)):
                    h = int(item["height"])

                ocr = item.get("ocrText") or item.get("ocr_text")
                ocr_str = str(ocr) if ocr is not None else None

                if (p_url or thumb) and ("image", p_url) not in seen_media:
                    seen_media.add(("image", p_url))
                    media_items.append(
                        Media(
                            type="image",
                            url=p_url,
                            thumbnail_url=thumb,
                            width=w,
                            height=h,
                            ocr_text=ocr_str,
                            metadata={},
                        )
                    )
        elif isinstance(item, str):
            if ("image", item) not in seen_media:
                seen_media.add(("image", item))
                media_items.append(
                    Media(
                        type="image",
                        url=item,
                        thumbnail_url=item,
                        width=None,
                        height=None,
                        ocr_text=None,
                        metadata={},
                    )
                )

    # Top-level video fields
    top_video = raw.get("video_url") or raw.get("videoUrl")
    if top_video and isinstance(top_video, str) and ("video", top_video) not in seen_media:
        seen_media.add(("video", top_video))
        v_thumb = raw.get("video_thumbnail_url") or raw.get("thumbnail") or raw.get("thumbnailUrl")
        media_items.append(
            Media(
                type="video",
                url=top_video,
                thumbnail_url=v_thumb if isinstance(v_thumb, str) else None,
                width=None,
                height=None,
                ocr_text=None,
                metadata={},
            )
        )

    # Top-level images list
    top_images = raw.get("images")
    if isinstance(top_images, list):
        for img in top_images:
            if isinstance(img, str) and ("image", img) not in seen_media:
                seen_media.add(("image", img))
                media_items.append(Media(type="image", url=img, thumbnail_url=img))
            elif isinstance(img, dict):
                u = img.get("url") or img.get("uri")
                t = img.get("thumbnail") or u
                if u and ("image", u) not in seen_media:
                    seen_media.add(("image", u))
                    img_w = int(img["width"]) if isinstance(img.get("width"), (int, float)) else None
                    img_h = int(img["height"]) if isinstance(img.get("height"), (int, float)) else None
                    media_items.append(
                        Media(
                            type="image",
                            url=u,
                            thumbnail_url=t,
                            width=img_w,
                            height=img_h,
                        )
                    )

    # Fallback to single image or thumbnail if no media yet
    if not media_items:
        fallback_img = raw.get("image") or raw.get("displayUrl") or raw.get("thumbnail")
        if fallback_img and isinstance(fallback_img, str) and ("image", fallback_img) not in seen_media:
            seen_media.add(("image", fallback_img))
            media_items.append(Media(type="image", url=fallback_img, thumbnail_url=fallback_img))

    # ── External Links ───────────────────────────────────────────────────────
    external_links: list[str] = []
    if raw.get("link") and isinstance(raw["link"], str):
        if raw["link"] not in external_links:
            external_links.append(raw["link"])

    text_refs = raw.get("textReferences")
    if isinstance(text_refs, list):
        for ref in text_refs:
            if isinstance(ref, dict):
                ref_url = ref.get("external_url") or ref.get("url")
                if ref_url and isinstance(ref_url, str) and ref_url not in external_links:
                    external_links.append(ref_url)

    if text:
        extracted = re.findall(r"https?://[^\s<>\"']+", text)
        for link in extracted:
            cleaned = link.rstrip(".,;!?:)")
            if cleaned not in external_links:
                external_links.append(cleaned)

    # ── Engagement & Platform Metadata ───────────────────────────────────────
    metadata: dict[str, Any] = {}
    likes = raw.get("likes") if raw.get("likes") is not None else raw.get("reactionLikeCount")
    if likes is not None:
        metadata["likes"] = likes

    comments = raw.get("comments") if raw.get("comments") is not None else raw.get("commentsCount")
    if comments is not None:
        metadata["comments"] = comments

    shares = raw.get("shares") if raw.get("shares") is not None else raw.get("sharesCount")
    if shares is not None:
        metadata["shares"] = shares

    views = raw.get("viewsCount") if raw.get("viewsCount") is not None else raw.get("videoPostViewCount")
    if views is not None:
        metadata["views"] = views

    # Platform-specific information (kept inside metadata)
    if raw.get("postId"):
        metadata["post_id"] = str(raw["postId"])
    if raw.get("pageName"):
        metadata["page_name"] = str(raw["pageName"])
    if raw.get("reactionLoveCount") is not None:
        metadata["reaction_love"] = raw["reactionLoveCount"]
    if raw.get("reactionHahaCount") is not None:
        metadata["reaction_haha"] = raw["reactionHahaCount"]
    if raw.get("reactionWowCount") is not None:
        metadata["reaction_wow"] = raw["reactionWowCount"]
    if raw.get("reactionSadCount") is not None:
        metadata["reaction_sad"] = raw["reactionSadCount"]
    if raw.get("reactionAngryCount") is not None:
        metadata["reaction_angry"] = raw["reactionAngryCount"]
    if raw.get("reactionCareCount") is not None:
        metadata["reaction_care"] = raw["reactionCareCount"]

    # ── Post URL ─────────────────────────────────────────────────────────────
    post_url = raw.get("url") or raw.get("topLevelUrl") or original_url

    return NormalizedPost(
        platform="facebook",
        url=post_url,
        author=author,
        text=text,
        published_at=published_at,
        media=media_items,
        external_links=external_links,
        metadata=metadata,
    )


# Alias for backwards compatibility
_normalise_item = normalize_facebook_post


class FacebookScraper(BasePlatformScraper):
    """Scrapes Facebook posts or pages using the configured Apify Actor."""

    def __init__(self) -> None:
        self._apify = ApifyService()
        self.last_result: ScrapeResult | None = None

    async def scrape(self, url: str) -> NormalizedPost:
        # 1. Validate URL shape before hitting Apify
        validate_facebook_url(url)

        actor_id = get_settings().apify_facebook_actor
        if not actor_id:
            raise RuntimeError(
                "APIFY_FACEBOOK_ACTOR is not configured. "
                "Set it in your .env file."
            )

        run_input = _build_actor_input(url)

        logger.info("Starting Facebook scrape for URL: %s", url)
        logger.info("Using Apify Actor: %s", actor_id)

        # 2. Run the Actor via the service layer
        items = await self._apify.run_actor(actor_id=actor_id, run_input=run_input)

        # 3. Validate dataset result
        if not items:
            raise RuntimeError(
                "Apify Actor returned an empty dataset. "
                "The post or page may be private, restricted, deleted, or no posts were found."
            )

        # 4. Select the matching item if multiple are returned
        raw = _select_best_item(items, requested_url=url)
        if not isinstance(raw, dict):
            raise RuntimeError(
                f"Unexpected Apify Actor response item type: {type(raw).__name__}. Expected dict."
            )

        # 5. Normalise and preserve raw result.
        normalized = normalize_facebook_post(raw, original_url=url)
        self.last_result = ScrapeResult(
            platform="facebook",
            raw_data=raw,
            normalized_data=normalized,
        )

        logger.info("Facebook scrape completed for URL: %s", url)
        return normalized
