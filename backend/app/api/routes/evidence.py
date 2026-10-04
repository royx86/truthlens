"""POST /api/v1/evidence/search route.

Searches web evidence for extracted claims requiring verification.
"""

from __future__ import annotations

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
from app.schemas.evidence import (
    EvidenceSearchRequest,
    EvidenceSearchResponse,
)
from app.schemas.post import ErrorResponse
from app.services.evidence_search_service import EvidenceSearchService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/evidence/search",
    response_model=EvidenceSearchResponse,
    responses={
        200: {
            "model": EvidenceSearchResponse,
            "description": "Successfully retrieved evidence for provided claims",
        },
        400: {"model": ErrorResponse, "description": "Invalid claims payload"},
        500: {"model": ErrorResponse, "description": "Unexpected evidence search failure"},
    },
)
async def search_evidence(request: EvidenceSearchRequest) -> JSONResponse:
    """Search external web evidence for each claim requiring verification."""
    job_id = generate_job_id()
    set_current_job_id(job_id)
    tracker = StageTracker(job_id=job_id)
    set_current_tracker(tracker)

    logger.info("Received evidence search request for %d claims", len(request.claims))

    try:
        async with timed_stage(
            "EVIDENCE_SEARCH",
            job_id=job_id,
            tracker=tracker,
            metadata={"claims_count": len(request.claims)},
        ):
            service = EvidenceSearchService()
            results = await service.search_for_claims(request.claims)

        response = EvidenceSearchResponse(
            status="success",
            results=results,
        )
        return JSONResponse(status_code=200, content=response.model_dump())

    except Exception as exc:
        logger.exception("Unexpected error during evidence search: %s", exc)
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                message=f"Evidence search failed unexpectedly: {str(exc)}",
            ).model_dump(),
        )
