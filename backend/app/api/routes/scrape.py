"""
POST /api/v1/scrape route.

Flow:
    ScrapeRequest (url)
        → detect_platform()
        → if unknown               → ErrorResponse (400)
        → if not yet implemented   → NotImplementedResponse (501)
        → Scraper.scrape()
            → validate URL
            → ApifyService.run_actor()
            → normalise
        → SuccessResponse (200)
"""

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.timing import (
    StageTracker,
    generate_job_id,
    set_current_job_id,
    set_current_tracker,
    timed_stage,
)
from app.platforms.detector import detect_platform
from app.schemas.post import (
    ErrorResponse,
    NotImplementedResponse,
    ScrapeRequest,
    SuccessResponse,
)
from app.services.scraper_service import (
    PlatformNotImplementedError,
    PlatformNotSupportedError,
    scrape_social_post,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/scrape",
    response_model=SuccessResponse,
    responses={
        200: {"model": SuccessResponse, "description": "Successfully scraped and normalized post"},
        400: {"model": ErrorResponse, "description": "Unsupported or invalid URL"},
        422: {"model": ErrorResponse, "description": "URL validation error"},
        501: {"model": NotImplementedResponse, "description": "Platform not implemented"},
        502: {"model": ErrorResponse, "description": "Scraper or external service error"},
        500: {"model": ErrorResponse, "description": "Unexpected server error"},
    },
)
async def scrape(request: ScrapeRequest) -> JSONResponse:
    """
    Accept a social-media URL, detect its platform, and scrape it.
    """
    job_id = generate_job_id()
    set_current_job_id(job_id)
    tracker = StageTracker(job_id=job_id)
    set_current_tracker(tracker)

    url = request.url.strip()
    logger.info("Received scrape request for URL: %s", url)

    try:
        async with timed_stage("REQUEST", job_id=job_id, tracker=tracker):
            post = await scrape_social_post(url)
            with timed_stage("RESPONSE", job_id=job_id, tracker=tracker):
                content = SuccessResponse(
                    platform=post.platform,
                    data=post,
                ).model_dump()
            return JSONResponse(
                status_code=200,
                content=content,
            )
    except PlatformNotSupportedError as exc:
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                platform=exc.platform,
                message=exc.message,
            ).model_dump(),
        )
    except PlatformNotImplementedError as exc:
        return JSONResponse(
            status_code=501,
            content=NotImplementedResponse(
                platform=exc.platform,
                message=exc.message,
            ).model_dump(),
        )
    except ValueError as exc:
        platform = detect_platform(url)
        logger.warning("%s URL validation failed: %s", platform.capitalize(), exc)
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(
                platform=platform,
                message=str(exc),
            ).model_dump(),
        )
    except RuntimeError as exc:
        platform = detect_platform(url)
        logger.error("%s scrape failed: %s", platform.capitalize(), exc)
        return JSONResponse(
            status_code=502,
            content=ErrorResponse(
                platform=platform,
                message=str(exc),
            ).model_dump(),
        )
    except Exception as exc:
        platform = detect_platform(url)
        logger.exception("Unexpected error during %s scrape", platform)
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                platform=platform,
                message="An unexpected error occurred. Please try again later.",
            ).model_dump(),
        )
    finally:
        tracker.log_summary()


