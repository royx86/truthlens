# Platforms package.
# Import scrapers here as they are implemented so the route can do:
#   from app.platforms import InstagramScraper
from app.platforms.facebook import FacebookScraper, normalize_facebook_post
from app.platforms.instagram import InstagramScraper, normalize_instagram_post

__all__ = [
    "InstagramScraper",
    "FacebookScraper",
    "normalize_instagram_post",
    "normalize_facebook_post",
]
