# TruthLens Backend — Milestone 1

Social-media URL scraping backend built with **FastAPI + Apify**.

> **Milestone 1 scope**: URL detection, Instagram scraping via Apify, normalized response.
> AI fact-checking, RAG, database, and authentication come in later milestones.

---

## Supported Platforms

| Platform   | Detected | Scraping |
|------------|----------|----------|
| Instagram  | ✅       | ✅ (posts & reels) |
| Facebook   | ✅       | ✅ (pages, posts, videos & reels) |
| Reddit     | ✅       | 🔜 not yet |
| Twitter/X  | ✅       | 🔜 not yet |
| Threads    | ✅       | 🔜 not yet |

---

## Quick Start

### 1. Prerequisites

- Python ≥ 3.11
- An [Apify](https://apify.com) account with an API token

### 2. Create a virtual environment and install dependencies using standard Python `venv`

Navigate to the `backend` directory:

```bash
cd backend
```

Create and activate a virtual environment:

```bash
# On Linux / macOS:
python3 -m venv .venv
source .venv/bin/activate

# On Windows (PowerShell):
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

*(For running unit tests, install dev dependencies: `pip install pytest pytest-asyncio httpx`)*

---

### 3. Configure environment variables inside `backend/.env`

The configuration file is located at `backend/.env` inside the project.

Copy the example configuration file:

```bash
cp .env.example .env
```

Edit `backend/.env`:

```env
APIFY_API_TOKEN=apify_api_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
APIFY_INSTAGRAM_ACTOR=apify/instagram-scraper
APIFY_FACEBOOK_ACTOR=apify/facebook-posts-scraper
```

#### Where to find your values

**`APIFY_API_TOKEN`**
1. Log in to [console.apify.com](https://console.apify.com).
2. Go to **Settings → Integrations → API tokens**.
3. Copy your **Personal API token**.

**`APIFY_INSTAGRAM_ACTOR`**
1. Browse the [Apify Store](https://apify.com/store) for an Instagram scraper Actor (e.g. `apify/instagram-scraper`).
2. Set to the exact Actor ID shown in the Apify Console.

**`APIFY_FACEBOOK_ACTOR`**
1. Uses the official Apify-maintained Facebook Posts Scraper: `apify/facebook-posts-scraper`.
2. Can be set or customized in `backend/.env`.

---

### 4. Verify the Actor's input schema

> **This is critical.** Different Instagram Actors on the Apify Store expect different input field names.

1. Open the Actor in the Apify Console.
2. Click the **Input** tab and check the JSON schema.
3. Confirm that `directUrls` is the correct field name.
4. If your Actor uses a different field (e.g. `urls`, `startUrls`), update `_build_actor_input()` in [`app/platforms/instagram.py`](app/platforms/instagram.py).

---

### 5. Start the server

Ensure your virtual environment is active, then run:

```bash
uvicorn app.main:app --reload
```

Swagger UI will be available at: **http://localhost:8000/docs**

#### 💡 Troubleshooting `[Errno 98] Address already in use`

If you encounter `ERROR: [Errno 98] Address already in use`, it means port 8000 is occupied by another process or background service.

You can resolve this by either:
1. **Changing the port**:
   ```bash
   uvicorn app.main:app --reload --port 8001
   ```
2. **Finding and stopping the process using port 8000**:
   ```bash
   # Find process PID
   fuser 8000/tcp
   # Or using lsof:
   lsof -i :8000

   # Kill the process
   fuser -k 8000/tcp
   ```

---

## API Reference

### Health check

```
GET /health
```

```json
{"status": "ok", "service": "truthlens-backend"}
```

### Scrape a URL

```
POST /api/v1/scrape
Content-Type: application/json

{"url": "https://www.instagram.com/p/XXXXXXXX/"}
```

#### Example curl (Instagram)

```bash
curl -X POST http://localhost:8000/api/v1/scrape \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.instagram.com/p/XXXXXXXX/"}'
```

Replace `XXXXXXXX` with a **real, public** Instagram post shortcode.

#### Example curl (Facebook)

```bash
curl -X POST http://localhost:8000/api/v1/scrape \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.facebook.com/example"
  }'
```

*(Use a real public Facebook page, post, video, or reel URL when testing, e.g. `https://www.facebook.com/cern`)*

---

## Example Responses

### ✅ Successful Instagram scrape

```json
{
  "status": "success",
  "platform": "instagram",
  "data": {
    "platform": "instagram",
    "url": "https://www.instagram.com/p/XXXXXXXX/",
    "author": "someuser",
    "author_url": "https://www.instagram.com/someuser/",
    "text": "Caption of the post…",
    "published_at": "2024-05-01T10:00:00+00:00",
    "media": [
      {
        "type": "image",
        "url": "https://cdn.instagram.com/…/image.jpg",
        "thumbnail_url": null
      }
    ],
    "metadata": { "…raw Apify item…": "…" }
  }
}
```

### ✅ Successful Facebook scrape

```json
{
  "status": "success",
  "platform": "facebook",
  "data": {
    "platform": "facebook",
    "url": "https://www.facebook.com/cern/posts/pfbid0kFrPhUvw4ATaGn8s4DWeATqsJzKmL8wvNhw6yLnH5YUVggxPqSMiiBns1iuaEWNSl",
    "author": "CERN",
    "author_url": "https://www.facebook.com/100064792144187",
    "text": "Back to school season 🎒 \n\n#ThrowbackThursday to the first edition of the CERN STEAM Academy...",
    "published_at": "2026-09-24T09:02:52.000Z",
    "media": [
      {
        "type": "image",
        "url": "https://scontent.xx.fbcdn.net/v/t39.99422-6/...",
        "thumbnail_url": "https://scontent.xx.fbcdn.net/v/t39.99422-6/..."
      }
    ],
    "metadata": {
      "postId": "1526627336173657",
      "pageName": "cern",
      "likes": 248,
      "comments": 3
    }
  }
}
```

### 🔜 Reddit (not implemented)

```bash
curl -X POST http://localhost:8000/api/v1/scrape \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.reddit.com/r/test/comments/abc123/"}'
```

```json
{
  "status": "not_implemented",
  "platform": "reddit",
  "message": "Reddit scraping is not implemented yet."
}
```

### ❌ Invalid / unknown URL

```bash
curl -X POST http://localhost:8000/api/v1/scrape \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/test"}'
```

```json
{
  "status": "error",
  "platform": "unknown",
  "message": "Unsupported or invalid URL."
}
```

### ❌ Instagram profile (not a post)

```bash
curl -X POST http://localhost:8000/api/v1/scrape \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.instagram.com/someuser/"}'
```

```json
{
  "status": "error",
  "platform": "instagram",
  "message": "Only Instagram post (/p/<id>/) and reel (/reel/<id>/) URLs are supported. Profile, hashtag, story, and explore URLs are not accepted."
}
```

### ❌ Facebook invalid URL / system page

```bash
curl -X POST http://localhost:8000/api/v1/scrape \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.facebook.com/"}'
```

```json
{
  "status": "error",
  "platform": "facebook",
  "message": "Invalid Facebook URL: Please provide a specific post, video, reel, or page URL (e.g., https://www.facebook.com/pagename or https://www.facebook.com/pagename/posts/123)."
}
```

---

## Running Tests

Run pytest inside your activated virtual environment:

```bash
pytest tests/ -v
```

---

## Docker

Build and run the backend in a container:

```bash
docker build -t truthlens-backend .
docker run -p 8000:8000 --env-file .env truthlens-backend
```

---

## Project Structure

```
backend/
├── app/
│   ├── main.py                   # FastAPI app, CORS, routes registration
│   ├── api/
│   │   └── routes/
│   │       └── scrape.py         # POST /api/v1/scrape endpoint (platform-independent)
│   ├── core/
│   │   └── config.py             # Settings (pydantic-settings, loads .env)
│   ├── platforms/
│   │   ├── __init__.py           # Exports InstagramScraper, FacebookScraper
│   │   ├── base.py               # BasePlatformScraper abstract class
│   │   ├── detector.py           # detect_platform(url) → platform name
│   │   ├── facebook.py           # FacebookScraper + URL validator + normaliser
│   │   └── instagram.py          # InstagramScraper + URL validator + normaliser
│   ├── schemas/
│   │   └── post.py               # NormalizedPost, Media, request/response models
│   └── services/
│       └── apify_service.py      # Async wrapper around Apify Python client
├── tests/
│   ├── test_api.py               # API route integration tests
│   ├── test_detector.py          # URL detector tests (no Apify needed)
│   ├── test_facebook_scraper.py  # Facebook scraper, validator & normalizer tests
│   └── test_instagram_validator.py  # Instagram URL validator tests
├── .env                          # Local environment variables (inside backend/)
├── .env.example                  # Environment variable template
├── .gitignore
├── Dockerfile
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

## Adding a New Platform

1. Create `app/platforms/<platform>.py` with a class inheriting `BasePlatformScraper`.
2. Implement `async def scrape(self, url: str) -> NormalizedPost`.
3. Export the scraper in `app/platforms/__init__.py`.
4. Register the scraper in `_SCRAPERS` in `app/api/routes/scrape.py`.
5. Remove the platform from `_NOT_IMPLEMENTED_MESSAGES` in `app/api/routes/scrape.py`.

