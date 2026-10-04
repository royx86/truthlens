"""
Instagram platform scraper and normalizer.

Responsibilities:
  1. Validate that the URL is an Instagram post or reel (not a profile / explore page).
  2. Delegate scraping to ApifyService.
  3. Store raw Apify data internally in ScrapeResult.
  4. Normalise the raw Apify Actor response into a universal NormalizedPost.
"""

from datetime import datetime, timezone
import logging
import re
from typing import Any

from app.core.config import get_settings
from app.platforms.base import BasePlatformScraper
from app.schemas.post import Author, Media, NormalizedPost, ScrapeResult
from app.services.apify_service import ApifyService

logger = logging.getLogger(__name__)

# Regex patterns for accepted Instagram URL paths.
# Accepts: /p/<id>/ and /reel/<id>/
_ACCEPTED_PATH_RE = re.compile(
    r"^/(?:p|reel)/[A-Za-z0-9_\-]+/?$",
    re.IGNORECASE,
)


def validate_instagram_url(url: str) -> None:
    """
    Raise ValueError if the URL is not an Instagram post or reel.

    We only parse the path portion so this function is independent of the
    platform detector (which already confirmed the host is instagram.com).
    """
    from urllib.parse import urlparse

    parsed = urlparse(url)
    path = parsed.path.rstrip("/")
    # Re-add trailing slash for the regex
    path_with_slash = path + "/"

    if not _ACCEPTED_PATH_RE.match(path_with_slash):
        raise ValueError(
            "Only Instagram post (/p/<id>/) and reel (/reel/<id>/) URLs are supported. "
            "Profile, hashtag, story, and explore URLs are not accepted."
        )


def _build_actor_input(url: str) -> dict[str, Any]:
    """Build the run_input dict for the Apify Instagram Actor."""
    return {
        "directUrls": [url],
    }


def normalize_instagram_post(raw: dict[str, Any], original_url: str) -> NormalizedPost:
    """
    Pure normalizer function converting raw Apify Instagram JSON into NormalizedPost.

    Extracts:
      - text from caption / text
      - published_at from timestamp (epoch converted to ISO string or direct string)
      - author into universal Author model
      - media (images, videos, reels, dimensions) into universal Media model
      - external_links from caption or externalUrl
      - engagement & platform identifiers into metadata
    """
    # ── Text ─────────────────────────────────────────────────────────────────
    text_val = raw.get("caption") or raw.get("text")
    text = str(text_val) if text_val is not None else None

    # ── Timestamps ───────────────────────────────────────────────────────────
    published_at_val = (
        raw.get("timestamp")
        or raw.get("takenAtTimestamp")
        or raw.get("taken_at_timestamp")
    )
    if isinstance(published_at_val, (int, float)):
        published_at = datetime.fromtimestamp(published_at_val, tz=timezone.utc).isoformat()
    elif published_at_val:
        published_at = str(published_at_val)
    else:
        published_at = None

    # ── Author ───────────────────────────────────────────────────────────────
    owner_obj = raw.get("owner") if isinstance(raw.get("owner"), dict) else {}
    username = raw.get("ownerUsername") or owner_obj.get("username") or raw.get("username")
    name = (
        raw.get("ownerFullName")
        or owner_obj.get("fullName")
        or raw.get("fullName")
        or raw.get("author")
        or username
    )
    owner_id_raw = raw.get("ownerId") or owner_obj.get("id") or raw.get("id")
    owner_id = str(owner_id_raw) if owner_id_raw is not None else None
    profile_pic = (
        raw.get("ownerProfilePicUrl")
        or owner_obj.get("profilePicUrl")
        or raw.get("profilePicUrl")
    )
    profile_url = f"https://www.instagram.com/{username}/" if username else None

    author: Author | None = None
    if username or name or owner_id or profile_pic:
        author = Author(
            name=name,
            username=username,
            profile_url=profile_url,
            profile_image_url=profile_pic,
            id=owner_id,
        )

    # ── Dimensions ───────────────────────────────────────────────────────────
    dims = raw.get("dimensions") if isinstance(raw.get("dimensions"), dict) else {}
    width_raw = raw.get("dimensionsWidth") or dims.get("width")
    height_raw = raw.get("dimensionsHeight") or dims.get("height")
    width = int(width_raw) if isinstance(width_raw, (int, float)) else None
    height = int(height_raw) if isinstance(height_raw, (int, float)) else None

    # ── Media ────────────────────────────────────────────────────────────────
    media_items: list[Media] = []
    seen_media: set[tuple[str, str | None]] = set()

    # Video post
    video_url = raw.get("videoUrl") or raw.get("video_url")
    display_url = raw.get("displayUrl") or raw.get("display_url")

    if video_url and isinstance(video_url, str):
        v_thumb = display_url or raw.get("thumbnailUrl") or raw.get("thumbnail_url")
        v_meta: dict[str, Any] = {}
        if raw.get("videoViewCount") is not None:
            v_meta["views"] = raw.get("videoViewCount")
        if raw.get("videoPlayCount") is not None:
            v_meta["plays"] = raw.get("videoPlayCount")
        if raw.get("videoDuration") is not None:
            v_meta["duration"] = raw.get("videoDuration")

        seen_media.add(("video", video_url))
        media_items.append(
            Media(
                type="video",
                url=video_url,
                thumbnail_url=v_thumb if isinstance(v_thumb, str) else None,
                width=width,
                height=height,
                ocr_text=None,
                metadata=v_meta,
            )
        )

    # Images list
    images = raw.get("images")
    if isinstance(images, list):
        for img in images:
            if isinstance(img, str):
                if ("image", img) not in seen_media:
                    seen_media.add(("image", img))
                    media_items.append(
                        Media(
                            type="image",
                            url=img,
                            thumbnail_url=None,
                            width=width,
                            height=height,
                            ocr_text=None,
                            metadata={},
                        )
                    )
            elif isinstance(img, dict):
                i_url = img.get("url") or img.get("display_url") or img.get("src")
                if i_url and ("image", i_url) not in seen_media:
                    seen_media.add(("image", i_url))
                    i_w = img.get("width")
                    i_h = img.get("height")
                    media_items.append(
                        Media(
                            type="image",
                            url=i_url,
                            thumbnail_url=img.get("thumbnail_url") or img.get("thumbnail"),
                            width=int(i_w) if isinstance(i_w, (int, float)) else width,
                            height=int(i_h) if isinstance(i_h, (int, float)) else height,
                            ocr_text=None,
                            metadata={},
                        )
                    )

    # Fallback to display_url if no media captured yet
    if not media_items and display_url and isinstance(display_url, str):
        if ("image", display_url) not in seen_media:
            seen_media.add(("image", display_url))
            media_items.append(
                Media(
                    type="image",
                    url=display_url,
                    thumbnail_url=None,
                    width=width,
                    height=height,
                    ocr_text=None,
                    metadata={},
                )
            )

    # ── External Links ───────────────────────────────────────────────────────
    external_links: list[str] = []
    if raw.get("externalUrl") and isinstance(raw["externalUrl"], str):
        external_links.append(raw["externalUrl"])

    if text:
        extracted = re.findall(r"https?://[^\s<>\"']+", text)
        for link in extracted:
            cleaned = link.rstrip(".,;!?:)")
            if cleaned not in external_links:
                external_links.append(cleaned)

    # ── Engagement & Platform Metadata ───────────────────────────────────────
    metadata: dict[str, Any] = {}
    likes = raw.get("likesCount") if raw.get("likesCount") is not None else raw.get("likes")
    if likes is not None:
        metadata["likes"] = likes

    comments = raw.get("commentsCount") if raw.get("commentsCount") is not None else raw.get("comments")
    if comments is not None:
        metadata["comments"] = comments

    views = raw.get("videoViewCount") if raw.get("videoViewCount") is not None else raw.get("videoPlayCount")
    if views is not None:
        metadata["views"] = views

    if raw.get("shortCode"):
        metadata["short_code"] = str(raw["shortCode"])
    if raw.get("id"):
        metadata["id"] = str(raw["id"])

    # ── Post URL ─────────────────────────────────────────────────────────────
    post_url = raw.get("url")
    if not post_url and raw.get("shortCode"):
        post_url = f"https://www.instagram.com/p/{raw['shortCode']}/"
    if not post_url:
        post_url = original_url

    return NormalizedPost(
        platform="instagram",
        url=post_url,
        author=author,
        text=text,
        published_at=published_at,
        media=media_items,
        external_links=external_links,
        metadata=metadata,
    )


class InstagramScraper(BasePlatformScraper):
    """Scrapes an Instagram post or reel using the configured Apify Actor."""

    def __init__(self) -> None:
        self._apify = ApifyService()
        self.last_result: ScrapeResult | None = None

    async def scrape(self, url: str) -> NormalizedPost:
        # 1. Validate the URL shape before hitting Apify.
        validate_instagram_url(url)

        actor_id = get_settings().apify_instagram_actor
        if not actor_id:
            raise RuntimeError(
                "APIFY_INSTAGRAM_ACTOR is not configured. "
                "Set it in your .env file."
            )

        run_input = _build_actor_input(url)

        logger.info("Starting Instagram scrape for URL: %s", url)
        logger.info("Using Apify Actor: %s", actor_id)

        # 2. Run the Actor via the service layer.
        items = await self._apify.run_actor(actor_id=actor_id, run_input=run_input)

        # 3. Validate the dataset result.
        if not items:
            raise RuntimeError(
                "Apify Actor returned an empty dataset. "
                "The post may be private, deleted, or the Actor input schema may be incorrect."
            )

        raw = items[0]
        if not isinstance(raw, dict):
            raise RuntimeError(
                f"Unexpected Apify Actor response type: {type(raw).__name__}. Expected dict."
            )

        # 4. Normalise and preserve raw result.
        normalized = normalize_instagram_post(raw, original_url=url)
        self.last_result = ScrapeResult(
            platform="instagram",
            raw_data=raw,
            normalized_data=normalized,
        )

        logger.info("Instagram scrape completed for URL: %s", url)
        return normalized
