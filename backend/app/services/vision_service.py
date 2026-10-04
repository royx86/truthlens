"""
Vision Analysis Service using Groq API and qwen/qwen3.8-27b.

Responsibilities:
- Visual observation only ("What is visually present?", not "Is the claim true?").
- Express uncertainty regarding identity, motives, or unobservable events.
- Never fact-check or verify claim truth.
- Produce structured JSON output matching VisualAnalysis schema.
"""

import base64
from dataclasses import dataclass
import io
import json
import logging
import os
import re
from typing import Any

from groq import AsyncGroq, BadRequestError
import httpx
from PIL import Image
from pydantic import ValidationError

from app.core.config import get_settings
from app.core.timing import timed_stage
from app.schemas.analysis import VisualAnalysis

logger = logging.getLogger(__name__)

FORBIDDEN_META_PHRASES = (
    "ground truth",
    "reference answer",
    "provided reference",
    "benchmark label",
    "benchmark",
    "expected identit",
    "reference for ground truth",
)


def _clean_text_field(text: str) -> str:
    """Remove any sentences mentioning external benchmarks or ground truth."""
    if not text:
        return text
    sentences = re.split(r"(?<=[.!?])\s+", text)
    cleaned = [
        s for s in sentences
        if not any(p in s.lower() for p in FORBIDDEN_META_PHRASES)
    ]
    return " ".join(cleaned).strip()

VISION_PROMPT = """You are the visual-analysis component of TruthLens.

Your task is to describe and structure what is visually observable in an image.
You are NOT the fact-checking component.
Do NOT determine whether a claim is true or false.
Do NOT infer real-world events from an image.
Do NOT treat text written on an image as proof that the described event happened.
Do NOT treat a person's apparent identity as independently verified.

Describe visual evidence separately from claims or assertions contained in the image.

CORE RULES:

1. IDENTITY RULE:
Do NOT attempt to independently identify real people from visual resemblance.
The visual analysis must describe observable physical characteristics (e.g., "Older man in a blue suit and red tie").
Always prefer setting identity to null.
Do NOT use visual identity recognition as evidence for a factual claim.
The textual claim itself can mention a named person when that name comes from the post text or visible image text.

Prefer:
{
  "description": "Older man in a blue suit and red tie",
  "identity": null,
  "identity_confidence": "unknown",
  "identity_basis": "Observable visual description only; identity not independently verified."
}

2. TEXT RULE:
Extract all text that is visibly present in the image into extracted_text (canonical transcription).
Also record text lines into visible_text list.
Set has_visible_text to true if text is visible, or false if the image contains no visible text.
Do NOT interpret visible text as a confirmed real-world event.
For example, if an image contains a headline claiming someone did something, record that verbatim in extracted_text.
Do NOT assert that the event occurred in description or observed_visual_details.

3. SCENE & DETAILS RULE:
Describe the visual scene objectively.
Record objective composition details in observed_visual_details (e.g., layout, background photograph, inset frames, text overlays).
If a person appears inside what looks like a coffin, describe: "A person lying inside what appears to be a coffin." Do NOT conclude that the person has died.

4. MANIPULATION & COMPOSITING RULE:
Describe visible compositing or editing characteristics in potential_manipulation_signals (e.g. text overlays, inset images, cropped photographs, digital graphics, watermarks, memes, social media graphics).
Do NOT declare an image fake solely because it contains editing or text overlays.

5. SATIRE & DISCLAIMER RULE:
If the image contains a disclaimer such as "NOT REAL", "SATIRE", or "PARODY", record that in visible_text and note it in observed_visual_details/uncertainty.
Do NOT independently issue a fact-check verdict.

6. UNCERTAINTY RULE:
Explicitly list what cannot be established visually in uncertainty (e.g. identity unverified, claims in text are unverified, context unknown).
Never fabricate details, never infer hidden events, motives, or what happened before or after the image.

7. NEVER MENTION EXTERNAL GROUND TRUTH:
The vision model must NEVER mention:
- reference answers
- ground truth
- benchmark labels
- expected identities
- names supplied outside the image
- "provided reference"
- comparisons between visual appearance and external names

The model only knows what is contained in the image itself.
If identity cannot be established:
{
  "identity": null,
  "identity_confidence": "uncertain",
  "identity_basis": "The person's identity cannot be established from the image alone."
}

Return only valid JSON matching this schema:
{
  "description": "objective visual summary of the graphic or photograph",
  "extracted_text": "all text visibly present in the image transcribed accurately, or empty string if no text is present",
  "has_visible_text": true | false,
  "people": [
    {
      "description": "visual appearance description (e.g. Older man in blue suit)",
      "identity": null,
      "identity_confidence": "unknown",
      "identity_basis": "Observable visual description only"
    }
  ],
  "objects": ["object 1", "object 2"],
  "scene": "setting description or null",
  "actions": ["visible physical action 1"],
  "visible_text": ["exact visible text 1", "exact visible text 2"],
  "observed_visual_details": ["visual detail 1", "visual detail 2"],
  "potential_manipulation_signals": ["visible artifact/overlay 1"],
  "uncertainty": ["area of uncertainty or ambiguity"]
}
"""

STRICT_JSON_SCHEMA: dict[str, Any] = {
    "name": "VisualAnalysis",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "description": {"type": "string"},
            "extracted_text": {"type": ["string", "null"]},
            "has_visible_text": {"type": ["boolean", "null"]},
            "people": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "description": {"type": "string"},
                        "identity": {"type": ["string", "null"]},
                        "identity_confidence": {
                            "type": ["string", "null"],
                            "enum": [
                                "certain_from_context",
                                "probable",
                                "uncertain",
                                "unknown",
                                None,
                            ],
                        },
                        "identity_basis": {"type": ["string", "null"]},
                    },
                    "required": ["description", "identity", "identity_confidence", "identity_basis"],
                    "additionalProperties": False,
                },
            },
            "objects": {"type": "array", "items": {"type": "string"}},
            "scene": {"type": ["string", "null"]},
            "actions": {"type": "array", "items": {"type": "string"}},
            "visible_text": {"type": "array", "items": {"type": "string"}},
            "observed_visual_details": {"type": "array", "items": {"type": "string"}},
            "potential_manipulation_signals": {"type": "array", "items": {"type": "string"}},
            "uncertainty": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "description",
            "extracted_text",
            "has_visible_text",
            "people",
            "objects",
            "scene",
            "actions",
            "visible_text",
            "observed_visual_details",
            "potential_manipulation_signals",
            "uncertainty",
        ],
        "additionalProperties": False,
    },
}


@dataclass
class VisionResult:
    analysis: VisualAnalysis | None
    success: bool
    error: str | None = None


class VisionService:
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.groq_api_key or os.getenv("GROQ_API_KEY", "")
        self.model = model or settings.groq_vision_model or os.getenv("GROQ_VISION_MODEL", "qwen/qwen3.8-27b")
        self._client: AsyncGroq | None = None

    def _get_client(self) -> AsyncGroq:
        if not self.api_key:
            raise ValueError("GROQ_API_KEY is not configured")
        if self._client is None:
            self._client = AsyncGroq(api_key=self.api_key)
        return self._client

    async def analyze_image_url(self, image_url: str | None) -> VisionResult:
        """
        Send image URL to Groq vision model and receive structured VisualAnalysis.
        Prefers direct remote URL, with graceful handling if inaccessible.
        """
        if not image_url or not image_url.strip():
            return VisionResult(analysis=None, success=False, error="Image URL is empty")

        try:
            client = self._get_client()
        except Exception as exc:
            logger.error("Groq client initialization failed: %s", exc)
            return VisionResult(analysis=None, success=False, error=str(exc))

        # First attempt with the direct image URL
        result = await self._call_groq_vision(client, image_url)
        if result.success:
            return result

        # If direct URL access failed on Groq's side (e.g. CDN restrictions / timeout / 400),
        # try fetching the image locally with proper browser headers and passing base64
        if "download" in (result.error or "").lower() or "inaccessible" in (result.error or "").lower():
            logger.info("Direct image URL not accessible by Groq; attempting base64 fallback for %s", image_url)
            fallback_b64 = await self._fetch_image_as_base64(image_url)
            if fallback_b64:
                b64_result = await self._call_groq_vision(client, fallback_b64)
                if b64_result.success:
                    return b64_result

        return result

    async def _call_groq_vision(self, client: AsyncGroq, image_input: str) -> VisionResult:
        """Execute chat completion with Groq vision model and parse structured output."""
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": VISION_PROMPT},
                    {"type": "image_url", "image_url": {"url": image_input}},
                ],
            }
        ]

        content = None
        # 1. Try strict json_schema first
        try:
            response = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={"type": "json_schema", "json_schema": STRICT_JSON_SCHEMA},
            )
            content = response.choices[0].message.content
        except (BadRequestError, Exception) as exc:
            logger.info("json_schema format not accepted or failed; falling back to json_object: %s", exc)
            try:
                response = await client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    response_format={"type": "json_object"},
                )
                content = response.choices[0].message.content
            except Exception as fallback_exc:
                logger.warning("Groq vision completion failed: %s", fallback_exc)
                return VisionResult(
                    analysis=None,
                    success=False,
                    error=f"Vision API error: {fallback_exc}",
                )

        if not content:
            return VisionResult(
                analysis=None,
                success=False,
                error="Empty response received from vision model",
            )

        # 2. Parse and validate JSON into VisualAnalysis model
        try:
            data = json.loads(content)
            # Ensure list fields default to list if null
            for list_field in (
                "people",
                "objects",
                "actions",
                "visible_text",
                "observed_visual_details",
                "potential_manipulation_signals",
                "uncertainty",
            ):
                if list_field not in data or data[list_field] is None:
                    data[list_field] = []

            # Clean description of any forbidden meta phrases
            if "description" in data and isinstance(data["description"], str):
                cleaned_desc = _clean_text_field(data["description"])
                data["description"] = cleaned_desc or data["description"]

            # Clean extracted_text of any forbidden meta phrases
            if "extracted_text" in data and isinstance(data["extracted_text"], str):
                cleaned_extracted = _clean_text_field(data["extracted_text"])
                data["extracted_text"] = cleaned_extracted if cleaned_extracted is not None else data["extracted_text"]

            # Filter out any list items containing forbidden meta phrases
            for list_field in (
                "objects",
                "actions",
                "visible_text",
                "observed_visual_details",
                "potential_manipulation_signals",
                "uncertainty",
            ):
                if isinstance(data.get(list_field), list):
                    data[list_field] = [
                        item for item in data[list_field]
                        if isinstance(item, str) and not any(p in item.lower() for p in FORBIDDEN_META_PHRASES)
                    ]

            # Synchronize canonical extracted_text and visible_text
            extracted_val = data.get("extracted_text")
            visible_list = data.get("visible_text") or []

            if (extracted_val is None or extracted_val == "") and visible_list:
                data["extracted_text"] = "\n".join(t for t in visible_list if isinstance(t, str) and t.strip())
            elif extracted_val and not visible_list:
                data["visible_text"] = [line.strip() for line in extracted_val.splitlines() if line.strip()]

            if "has_visible_text" not in data or data["has_visible_text"] is None:
                has_text = bool((data.get("extracted_text") and data["extracted_text"].strip()) or (data.get("visible_text") and len(data["visible_text"]) > 0))
                data["has_visible_text"] = has_text

            # Sanitize people list to ensure valid Literal confidence and basis, and no ground truth leakage
            if isinstance(data.get("people"), list):
                for person in data["people"]:
                    if isinstance(person, dict):
                        ident_str = str(person.get("identity") or "").lower()
                        basis_str = str(person.get("identity_basis") or "").lower()

                        # If person identity or basis references ground truth or external benchmarks, reset
                        if any(p in ident_str for p in FORBIDDEN_META_PHRASES) or any(p in basis_str for p in FORBIDDEN_META_PHRASES):
                            person["identity"] = None
                            person["identity_confidence"] = "uncertain"
                            person["identity_basis"] = "The person's identity cannot be established from the image alone."
                        else:
                            if person.get("identity_basis"):
                                cleaned_basis = _clean_text_field(person["identity_basis"])
                                person["identity_basis"] = cleaned_basis or "The person's identity cannot be established from the image alone."
                            else:
                                person["identity_basis"] = "The person's identity cannot be established from the image alone."

                            if person.get("description"):
                                person["description"] = _clean_text_field(person["description"]) or person["description"]

                        conf = person.get("identity_confidence")
                        if conf not in ("certain_from_context", "probable", "uncertain", "unknown", None):
                            conf_str = str(conf).lower()
                            if conf_str in ("high", "certain", "very high"):
                                person["identity_confidence"] = "probable"
                            elif conf_str in ("low", "medium", "uncertain", "tentative"):
                                person["identity_confidence"] = "uncertain"
                            else:
                                person["identity_confidence"] = "unknown"

            analysis = VisualAnalysis.model_validate(data)
            return VisionResult(analysis=analysis, success=True, error=None)
        except (json.JSONDecodeError, ValidationError) as exc:
            logger.warning("Failed to validate vision output: %s (content: %r)", exc, content[:200])
            return VisionResult(
                analysis=None,
                success=False,
                error=f"Invalid vision output structure: {exc}",
            )

    async def _fetch_image_as_base64(self, image_url: str) -> str | None:
        """Download remote image and format as data URL if directly accessible."""
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
        }
        try:
            async with timed_stage("MEDIA_DOWNLOAD"):
                async with httpx.AsyncClient(headers=headers, timeout=15.0, follow_redirects=True) as client:
                    resp = await client.get(image_url)
                    resp.raise_for_status()
                    # Verify valid image and enforce dimensions >= 32
                    img = Image.open(io.BytesIO(resp.content))
                    if img.width < 32 or img.height < 32:
                        return None
                    mime = Image.MIME.get(img.format, "image/jpeg")
                    b64_str = base64.b64encode(resp.content).decode("utf-8")
                    return f"data:{mime};base64,{b64_str}"
        except Exception as exc:
            logger.warning("Base64 fetch fallback failed for %s: %s", image_url, exc)
            return None
