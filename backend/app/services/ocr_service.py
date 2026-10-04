"""
OCR Service for extracting physically visible text from images using Tesseract OCR.

Flow:
    image URL
        ↓
    download image (httpx)
        ↓
    Tesseract (pytesseract in asyncio thread pool)
        ↓
    OCRResult(text, success, error)
"""

import asyncio
from dataclasses import dataclass
import io
import logging
import shutil

import httpx
from PIL import Image, UnidentifiedImageError
import pytesseract

from app.core.timing import timed_stage

logger = logging.getLogger(__name__)

DOWNLOAD_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
}


@dataclass
class OCRResult:
    text: str
    success: bool
    error: str | None = None


class OCRService:
    def __init__(self, timeout_seconds: float = 15.0) -> None:
        self.timeout_seconds = timeout_seconds

    @staticmethod
    def is_tesseract_available() -> bool:
        """Check if tesseract binary is accessible in system PATH."""
        return shutil.which("tesseract") is not None

    async def extract_text_from_url(self, image_url: str | None) -> OCRResult:
        """
        Download image from image_url and run Tesseract OCR.
        Never crashes; returns an OCRResult with error info if unsuccessful.
        """
        if not image_url or not image_url.strip():
            return OCRResult(text="", success=False, error="Image URL is empty")

        if not self.is_tesseract_available():
            logger.warning("Tesseract binary not found in PATH")
            return OCRResult(
                text="",
                success=False,
                error="Tesseract binary not installed on system",
            )

        # 1. Download image
        try:
            async with timed_stage("MEDIA_DOWNLOAD"):
                async with httpx.AsyncClient(
                    headers=DOWNLOAD_HEADERS,
                    timeout=self.timeout_seconds,
                    follow_redirects=True,
                ) as client:
                    response = await client.get(image_url)
                    response.raise_for_status()
                    image_bytes = response.content
        except httpx.HTTPError as exc:
            logger.warning("Failed to download image from %s: %s", image_url, exc)
            return OCRResult(
                text="",
                success=False,
                error=f"Image download failed: {exc}",
            )
        except Exception as exc:
            logger.warning("Unexpected error downloading image from %s: %s", image_url, exc)
            return OCRResult(
                text="",
                success=False,
                error=f"Download failed: {exc}",
            )

        # 2. Extract text from downloaded bytes
        return await self.extract_text_from_bytes(image_bytes)

    async def extract_text_from_bytes(self, image_bytes: bytes) -> OCRResult:
        """Process raw image bytes with Tesseract."""
        if not image_bytes:
            return OCRResult(text="", success=False, error="Image payload is empty")

        if not self.is_tesseract_available():
            return OCRResult(
                text="",
                success=False,
                error="Tesseract binary not installed on system",
            )

        try:
            image = Image.open(io.BytesIO(image_bytes))
            # Convert to RGB if needed (handles RGBA, P, etc.)
            if image.mode not in ("RGB", "L"):
                image = image.convert("RGB")

            raw_text = await asyncio.to_thread(pytesseract.image_to_string, image)
            cleaned_text = raw_text.strip()
            return OCRResult(text=cleaned_text, success=True, error=None)
        except pytesseract.TesseractNotFoundError:
            logger.warning("Tesseract binary not found during execution")
            return OCRResult(
                text="",
                success=False,
                error="Tesseract binary not installed on system",
            )
        except UnidentifiedImageError as exc:
            logger.warning("Invalid image bytes: %s", exc)
            return OCRResult(
                text="",
                success=False,
                error=f"Invalid image format: {exc}",
            )
        except Exception as exc:
            logger.warning("OCR processing error: %s", exc)
            return OCRResult(
                text="",
                success=False,
                error=f"OCR execution failed: {exc}",
            )
