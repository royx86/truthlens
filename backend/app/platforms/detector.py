"""
URL platform detector.

Uses urllib.parse.urlparse to safely identify which social-media platform a URL
belongs to.  Does NOT use substring search on the raw URL string.

Supported platforms: instagram, reddit, facebook, twitter, threads
Unknown or unrecognised hosts return "unknown".
"""

from urllib.parse import urlparse


# Map of normalised hostname → platform name.
# Order matters only for documentation clarity; dict lookup is O(1).
_HOSTNAME_MAP: dict[str, str] = {
    # Instagram
    "instagram.com": "instagram",
    "instagr.am": "instagram",
    # Reddit
    "reddit.com": "reddit",
    "old.reddit.com": "reddit",
    "new.reddit.com": "reddit",
    # Facebook
    "facebook.com": "facebook",
    "fb.watch": "facebook",
    "fb.com": "facebook",
    "m.facebook.com": "facebook",
    "web.facebook.com": "facebook",
    # Twitter / X
    "twitter.com": "twitter",
    "x.com": "twitter",
    "t.co": "twitter",
    # Threads
    "threads.net": "threads",
}


def _normalise_url(url: str) -> str:
    """
    Ensure the URL has a scheme so urlparse works correctly.

    If the caller passes 'instagram.com/p/ABC123' (no scheme), we prepend
    'https://' so that urlparse can extract the hostname.  We do NOT silently
    accept obviously non-URL strings (e.g. bare words without a dot).
    """
    url = url.strip()
    if not url:
        return url
    # Add scheme only when the URL looks like it might be a bare hostname/path.
    if "://" not in url:
        url = "https://" + url
    return url


def _extract_hostname(url: str) -> str:
    """
    Parse the URL and return a lowercased hostname with 'www.' stripped.
    Returns an empty string if parsing fails or produces no hostname.
    """
    try:
        parsed = urlparse(url)
        hostname = (parsed.hostname or "").lower()
        # Strip leading 'www.' prefix so 'www.instagram.com' → 'instagram.com'
        if hostname.startswith("www."):
            hostname = hostname[4:]
        return hostname
    except Exception:
        return ""


def detect_platform(url: str) -> str:
    """
    Detect which social-media platform a URL belongs to.

    Returns one of:
        "instagram" | "reddit" | "facebook" | "twitter" | "threads" | "unknown"
    """
    normalised = _normalise_url(url)
    hostname = _extract_hostname(normalised)

    if not hostname or "." not in hostname:
        # Not a parsable URL (e.g. a bare word, empty string).
        return "unknown"

    return _HOSTNAME_MAP.get(hostname, "unknown")
