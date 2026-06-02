"""Extract training plan text from uploaded images or PDFs."""

from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Any, Dict, Optional

import fitz
from openai import OpenAI

ALLOWED_MIME_TYPES = frozenset(
    {
        "image/jpeg",
        "image/png",
        "image/webp",
        "application/pdf",
    }
)

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024
MAX_VISION_PAGES = 10
TEXT_LAYER_CHAR_THRESHOLD = 200


class UnsupportedMediaTypeError(ValueError):
    """Raised when the uploaded file type is not supported."""


class FileTooLargeError(ValueError):
    """Raised when the uploaded file exceeds the size limit."""


class EmptyExtractionError(ValueError):
    """Raised when no text could be extracted from the file."""


def vision_model() -> str:
    return os.getenv("OPENAI_VISION_MODEL", "gpt-4o")


def resolve_mime_type(
    file_bytes: bytes,
    content_type: str | None,
    filename: str | None,
) -> str:
    """Normalize browser MIME, sniff magic bytes, then fall back to extension."""
    mime = (content_type or "").split(";")[0].strip().lower()
    if mime in ("image/jpg", "image/pjpeg"):
        mime = "image/jpeg"
    if mime in ALLOWED_MIME_TYPES:
        return mime

    if file_bytes.startswith(b"%PDF"):
        return "application/pdf"
    if file_bytes.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if file_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(file_bytes) >= 12 and file_bytes[:4] == b"RIFF" and file_bytes[8:12] == b"WEBP":
        return "image/webp"

    ext = Path(filename or "").suffix.lower()
    ext_map = {
        ".pdf": "application/pdf",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }
    if ext in ext_map:
        return ext_map[ext]

    return mime


def validate_upload(*, mime_type: str, size_bytes: int) -> None:
    if mime_type not in ALLOWED_MIME_TYPES:
        raise UnsupportedMediaTypeError(
            f"Unsupported file type: {mime_type or 'unknown'}. "
            f"Allowed: JPEG, PNG, WebP, PDF."
        )
    if size_bytes > MAX_FILE_SIZE_BYTES:
        raise FileTooLargeError(
            f"File too large ({size_bytes} bytes). Maximum is {MAX_FILE_SIZE_BYTES} bytes."
        )
    if size_bytes == 0:
        raise EmptyExtractionError("Uploaded file is empty.")


def _extract_from_image_bytes(
    image_bytes: bytes,
    mime_type: str,
    *,
    client: OpenAI,
    model: str,
    prompt: str,
) -> str:
    b64 = base64.standard_b64encode(image_bytes).decode("ascii")
    data_url = f"data:{mime_type};base64,{b64}"
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ],
    )
    return (response.choices[0].message.content or "").strip()


def _pdf_text_layer(pdf_bytes: bytes) -> tuple[str, int]:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        page_count = len(doc)
        parts = [page.get_text() for page in doc]
        return "\n".join(parts).strip(), page_count
    finally:
        doc.close()


def _pdf_page_pngs(pdf_bytes: bytes, max_pages: int) -> list[bytes]:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        images: list[bytes] = []
        for i, page in enumerate(doc):
            if i >= max_pages:
                break
            pix = page.get_pixmap(dpi=150)
            images.append(pix.tobytes("png"))
        return images
    finally:
        doc.close()


def extract_training_plan_text(
    file_bytes: bytes,
    mime_type: str,
    *,
    client: OpenAI,
    extraction_prompt: str,
    model: Optional[str] = None,
    max_vision_pages: int = MAX_VISION_PAGES,
) -> Dict[str, Any]:
    """
    Convert uploaded bytes + MIME type to extracted plan text.

    Returns dict with keys: extracted_text, page_count (PDF only, else omitted).
    """
    validate_upload(mime_type=mime_type, size_bytes=len(file_bytes))

    vision = model or vision_model()
    page_count: Optional[int] = None

    if mime_type.startswith("image/"):
        extracted = _extract_from_image_bytes(
            file_bytes,
            mime_type,
            client=client,
            model=vision,
            prompt=extraction_prompt,
        )
    elif mime_type == "application/pdf":
        text_layer, page_count = _pdf_text_layer(file_bytes)
        if len(text_layer) >= TEXT_LAYER_CHAR_THRESHOLD:
            extracted = text_layer
        else:
            page_images = _pdf_page_pngs(file_bytes, max_vision_pages)
            if not page_images:
                raise EmptyExtractionError("PDF has no pages.")
            parts: list[str] = []
            for page_idx, png_bytes in enumerate(page_images, start=1):
                page_text = _extract_from_image_bytes(
                    png_bytes,
                    "image/png",
                    client=client,
                    model=vision,
                    prompt=extraction_prompt,
                )
                if page_text:
                    parts.append(f"--- Page {page_idx} ---\n{page_text}")
            extracted = "\n\n".join(parts).strip()
    else:
        raise UnsupportedMediaTypeError(f"Unsupported file type: {mime_type}")

    if not extracted:
        raise EmptyExtractionError("Could not extract any text from the file.")

    result: Dict[str, Any] = {"extracted_text": extracted}
    if page_count is not None:
        result["page_count"] = page_count
    return result
