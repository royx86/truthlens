"""TruthLens schemas package."""

from app.schemas.analysis import (
    AnalysisInput,
    AnalysisResponse,
    AnalyzeRequest,
    AnalyzedMedia,
    Claim,
    ClaimExtractionResult,
    PersonAnalysis,
    SourceInfo,
    VisualAnalysis,
)
from app.schemas.evidence import (
    ClaimEvidence,
    Evidence,
    EvidenceSearchRequest,
    EvidenceSearchResponse,
)
from app.schemas.post import (
    Author,
    ErrorResponse,
    Media,
    NormalizedPost,
    NotImplementedResponse,
    ScrapeRequest,
    ScrapeResult,
    SuccessResponse,
)
from app.schemas.auth import (
    AuthResponse,
    UserLogin,
    UserResponse,
    UserSignUp,
)
from app.schemas.report import (
    ClaimAssessment,
    ClaimEvidenceSources,
    FactCheckAnalysis,
    RankedEvidence,
    UnifiedAnalysisData,
    UnifiedAnalysisResponse,
)

__all__ = [
    # Post / Scraping
    "Author",
    "ErrorResponse",
    "Media",
    "NormalizedPost",
    "NotImplementedResponse",
    "ScrapeRequest",
    "ScrapeResult",
    "SuccessResponse",
    # Analysis & Vision
    "AnalysisInput",
    "AnalysisResponse",
    "AnalyzeRequest",
    "AnalyzedMedia",
    "Claim",
    "ClaimExtractionResult",
    "PersonAnalysis",
    "SourceInfo",
    "VisualAnalysis",
    # Evidence Search
    "ClaimEvidence",
    "Evidence",
    "EvidenceSearchRequest",
    "EvidenceSearchResponse",
    # Report & Unified Analysis
    "ClaimAssessment",
    "ClaimEvidenceSources",
    "FactCheckAnalysis",
    "RankedEvidence",
    "UnifiedAnalysisData",
    "UnifiedAnalysisResponse",
]
