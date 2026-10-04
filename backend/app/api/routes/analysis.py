"""POST /api/v1/analyze route.

Primary unified analysis endpoint for TruthLens.
Orchestrates the complete fact-checking verification pipeline:
Scraping → Media Analysis → Claim Extraction → Evidence Search → Evidence Ranking → Fact-Check Reasoning → Final Report.
"""

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.platforms.detector import detect_platform
from app.schemas.analysis import AnalyzeRequest
from app.schemas.post import (
    ErrorResponse,
    NotImplementedResponse,
)
from app.schemas.report import UnifiedAnalysisResponse
from app.services.analysis_service import AnalysisService
from app.services.scraper_service import (
    PlatformNotImplementedError,
    PlatformNotSupportedError,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/analyze",
    response_model=UnifiedAnalysisResponse,
    responses={
        200: {
            "model": UnifiedAnalysisResponse,
            "description": "Successfully ran complete end-to-end fact-checking analysis",
        },
        400: {"model": ErrorResponse, "description": "Unsupported or invalid URL"},
        422: {"model": ErrorResponse, "description": "URL validation error"},
        501: {"model": NotImplementedResponse, "description": "Platform not implemented"},
        502: {"model": ErrorResponse, "description": "Scraper or external service error"},
        500: {"model": ErrorResponse, "description": "Unexpected server error"},
    },
)
async def analyze(request: AnalyzeRequest) -> JSONResponse:
    """Accept a social-media URL and execute the complete TruthLens analysis pipeline."""
    url = request.url.strip()
    logger.info("Received unified analyze request for URL: %s", url)

    try:
        service = AnalysisService()
        result = await service.analyze_url(url)
        return JSONResponse(
            status_code=200,
            content=result.model_dump(),
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
        logger.warning("URL validation failed for %s: %s", url, exc)
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(
                platform=platform,
                message=str(exc),
            ).model_dump(),
        )
    except RuntimeError as exc:
        platform = detect_platform(url)
        logger.error("Scraper execution error for %s: %s", url, exc)
        return JSONResponse(
            status_code=502,
            content=ErrorResponse(
                platform=platform,
                message=str(exc),
            ).model_dump(),
        )
    except Exception as exc:
        platform = detect_platform(url)
        logger.exception("Unexpected error during analysis of %s: %s", url, exc)
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                platform=platform,
                message="An unexpected error occurred. Please try again later.",
            ).model_dump(),
        )
