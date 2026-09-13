"""Part 4: voice and image helpers for KhataGuard.

Non-destructive design:
- Audio/image bytes are sent to Groq only when the caller explicitly invokes a function.
- Existing Part 3 transaction parser is injected as a callable; its prompt is not copied or changed here.
- No database write happens in this module.
"""
from __future__ import annotations

import base64
import inspect
import io
import json
import mimetypes
import requests
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from PIL import Image, UnidentifiedImageError


ALLOWED_AUDIO_SUFFIXES = {".wav", ".mp3", ".m4a"}
ALLOWED_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg"}
MAX_AUDIO_BYTES = 24 * 1024 * 1024  # stay below Groq free-tier 25 MB boundary
MAX_IMAGE_BYTES = 10 * 1024 * 1024
DEFAULT_SPEECH_MODEL = "whisper-large-v3-turbo"
DEFAULT_VISION_MODEL = "llama-3.2-11b-vision-preview"


class MediaProcessingError(RuntimeError):
    """User-safe error raised for Part 4 processing failures."""


@dataclass(frozen=True)
class ParsedTransaction:
    customer: str
    sale: float
    paid: float

    def as_dict(self) -> dict[str, Any]:
        return {"customer": self.customer, "sale": self.sale, "paid": self.paid}


def _client(api_key: str, *, timeout: float = 45.0):
    if not api_key or not api_key.strip():
        raise MediaProcessingError("GROQ_API_KEY missing hai.")
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise MediaProcessingError("openai package install nahi hai. requirements.txt run karein.") from exc
    return OpenAI(
        api_key=api_key.strip(),
        base_url="https://api.groq.com/openai/v1",
        timeout=timeout,
        max_retries=1,
    )


def _suffix(filename: str) -> str:
    return Path(filename or "").suffix.lower()


def _audio_mime(filename: str) -> str:
    suffix = _suffix(filename)
    return {
        ".wav": "audio/wav",
        ".mp3": "audio/mpeg",
        ".m4a": "audio/mp4",
    }.get(suffix, mimetypes.guess_type(filename)[0] or "application/octet-stream")


def validate_audio(audio_bytes: bytes, filename: str) -> None:
    if not audio_bytes:
        raise MediaProcessingError("Audio file khaali hai.")
    if _suffix(filename) not in ALLOWED_AUDIO_SUFFIXES:
        raise MediaProcessingError("Sirf WAV, MP3, ya M4A audio upload karein.")
    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise MediaProcessingError("Audio 24 MB se chhota rakhein.")


def validate_image(image_bytes: bytes, filename: str) -> str:
    if not image_bytes:
        raise MediaProcessingError("Image file khaali hai.")
    suffix = _suffix(filename)
    if suffix not in ALLOWED_IMAGE_SUFFIXES:
        raise MediaProcessingError("Sirf PNG, JPG, ya JPEG image upload karein.")
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise MediaProcessingError("Image 10 MB se chhoti rakhein.")

    try:
        with Image.open(io.BytesIO(image_bytes)) as image:
            image.verify()
            detected = (image.format or "").upper()
    except (UnidentifiedImageError, OSError) as exc:
        raise MediaProcessingError("Image valid/corrupted nahi lag rahi.") from exc

    allowed_detected = {"PNG", "JPEG"}
    if detected not in allowed_detected:
        raise MediaProcessingError("Image content PNG/JPEG nahi hai.")
    return "image/png" if detected == "PNG" else "image/jpeg"


def _groq_error_message(status_code: int, detail: str, kind: str) -> str:
    if status_code == 401:
        return "Groq API key invalid/expired hai (401). Apni GROQ_API_KEY dobara check karein."
    if status_code == 403:
        return f"Groq ne {kind} model ko allow nahi kiya (403). Model permission check karein. Details: {detail}"
    if status_code == 429:
        return f"Groq rate/quota limit hit hui (429). Thori der baad dobara try karein. Details: {detail}"
    if status_code == 413:
        return f"{kind.capitalize()} request bohat bari hai (413). Chhoti file upload karein."
    if status_code == 400:
        return f"Groq ne {kind} request reject ki (400). Details: {detail}"
    return f"Groq {kind} error ({status_code}). Details: {detail}"


def _response_detail(response: requests.Response) -> str:
    try:
        body = response.json()
        error = body.get("error", {}) if isinstance(body, dict) else {}
        return str(error.get("message") or body)[:800]
    except ValueError:
        return response.text[:800]


def transcribe_audio(
    *,
    audio_bytes: bytes,
    filename: str,
    api_key: str,
    speech_model: str = DEFAULT_SPEECH_MODEL,
    language: str | None = None,
    timeout: float = 60.0,
) -> str:
    """Transcribe Urdu/Roman Urdu/English audio using Groq Whisper."""
    validate_audio(audio_bytes, filename)
    if not api_key or not api_key.strip():
        raise MediaProcessingError("GROQ_API_KEY missing hai.")

    data = {"model": speech_model, "response_format": "json", "temperature": "0"}
    if language in {"ur", "en"}:
        data["language"] = language

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {api_key.strip()}"},
            data=data,
            files={"file": (filename, audio_bytes, _audio_mime(filename))},
            timeout=timeout,
        )
    except requests.RequestException as exc:
        raise MediaProcessingError(
            "Groq se connection nahi ho rahi. Internet connection check karein aur dobara try karein."
        ) from exc

    if response.status_code != 200:
        detail = _response_detail(response)
        raise MediaProcessingError(_groq_error_message(response.status_code, detail, "voice"))

    try:
        body = response.json()
        text = str(body.get("text") or "").strip()
    except (ValueError, AttributeError) as exc:
        raise MediaProcessingError("Groq voice response samajh nahi aaya. Dobara try karein.") from exc

    if not text:
        raise MediaProcessingError("Audio se koi text nahi mila.")
    return text


def ocr_handwritten_image(
    *,
    image_bytes: bytes,
    filename: str,
    api_key: str,
    vision_model: str = DEFAULT_VISION_MODEL,
    timeout: float = 60.0,
) -> str:
    """Read a handwritten khata image into text only using Groq Vision."""
    mime = validate_image(image_bytes, filename)
    encoded = base64.b64encode(image_bytes).decode("ascii")
    data_url = f"data:{mime};base64,{encoded}"

    system_prompt = (
        "You are an OCR reader for a Pakistani shop ledger. Read the handwritten or printed "
        "transaction text from the image as faithfully as possible. Preserve names, amounts, "
        "Urdu/Roman Urdu/English wording and visible date. Do not calculate balances, do not "
        "invent missing values, and do not convert the content into JSON. Return only the "
        "transcribed ledger text."
    )
    payload = {
        "model": vision_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Transcribe this khata entry."},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            },
        ],
        "temperature": 0,
        "max_completion_tokens": 800,
    }

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key.strip()}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=timeout,
        )
    except requests.RequestException as exc:
        raise MediaProcessingError(
            "Groq se connection nahi ho rahi. Internet connection check karein aur dobara try karein."
        ) from exc

    if response.status_code != 200:
        detail = ""
        try:
            body = response.json()
            error = body.get("error", {}) if isinstance(body, dict) else {}
            detail = str(error.get("message") or body)
        except ValueError:
            detail = response.text[:500]

        if response.status_code == 401:
            raise MediaProcessingError("Groq API key invalid/expired hai (401). Apni GROQ_API_KEY dobara check karein.")
        if response.status_code == 403:
            raise MediaProcessingError(f"Groq ne vision model ko allow nahi kiya (403). Model permission check karein. Details: {detail}")
        if response.status_code == 429:
            raise MediaProcessingError(f"Groq rate/quota limit hit hui (429). Thori der baad dobara try karein. Details: {detail}")
        if response.status_code == 413:
            raise MediaProcessingError("Image request bohat bari hai (413). Chhoti image upload karein.")
        if response.status_code == 400:
            raise MediaProcessingError(f"Groq ne image request reject ki (400). Details: {detail}")
        raise MediaProcessingError(f"Groq Vision error ({response.status_code}). Details: {detail}")

    try:
        body = response.json()
        text = (body["choices"][0]["message"].get("content") or "").strip()
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise MediaProcessingError("Groq ka response samajh nahi aaya. Dobara try karein.") from exc

    if not text:
        raise MediaProcessingError("Image se readable text nahi mila.")
    return text


def _call_existing_parser(
    parser: Callable[..., Any],
    text: str,
    *,
    api_key: str,
    model: str,
) -> Any:
    """Call Part 3 parser without assuming one exact historical signature."""
    parameters = inspect.signature(parser).parameters
    kwargs: dict[str, Any] = {}
    if "api_key" in parameters:
        kwargs["api_key"] = api_key
    if "model" in parameters:
        kwargs["model"] = model
    return parser(text, **kwargs)


def normalize_parser_result(result: Any) -> ParsedTransaction:
    """Validate the minimum contract expected from the existing Part 3 parser."""
    if not isinstance(result, dict):
        raise MediaProcessingError("AI parser ka response valid object nahi hai.")

    if result.get("needs_clarification") is True:
        question = result.get("question")
        raise MediaProcessingError(
            question.strip() if isinstance(question, str) and question.strip()
            else "Transaction ki details clear nahi hain."
        )

    customer = result.get("customer")
    if not isinstance(customer, str) or not customer.strip():
        raise MediaProcessingError("Customer name clear nahi mila.")

    amounts: list[float] = []
    for field in ("sale", "paid"):
        raw = result.get(field)
        if isinstance(raw, bool) or raw is None:
            raise MediaProcessingError(f"{field.title()} amount clear nahi mila.")
        try:
            amount = float(raw)
        except (TypeError, ValueError) as exc:
            raise MediaProcessingError(f"{field.title()} valid number nahi hai.") from exc
        if amount < 0:
            raise MediaProcessingError(f"{field.title()} negative nahi ho sakta.")
        amounts.append(amount)

    sale, paid = amounts
    if sale == 0 and paid == 0:
        raise MediaProcessingError("Sale ya payment zero se greater honi chahiye.")

    return ParsedTransaction(customer=customer.strip(), sale=sale, paid=paid)


def parse_with_existing_ai(
    *,
    text: str,
    parser: Callable[..., Any],
    api_key: str,
    text_model: str,
) -> ParsedTransaction:
    if not text or not text.strip():
        raise MediaProcessingError("AI ko bhejne ke liye text khaali hai.")
    try:
        raw = _call_existing_parser(
            parser,
            text.strip(),
            api_key=api_key,
            model=text_model,
        )
    except MediaProcessingError:
        raise
    except Exception as exc:
        raise MediaProcessingError(f"Existing Part 3 AI parser transaction samajh nahi saka: {str(exc)}") from exc
    return normalize_parser_result(raw)
