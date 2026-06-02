#!/usr/bin/env python3
"""Tests for document import (MIME validation, PDF text layer, mocked vision)."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import fitz

_SRC = Path(__file__).resolve().parents[1]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from document_import import (  # noqa: E402
    EmptyExtractionError,
    FileTooLargeError,
    UnsupportedMediaTypeError,
    extract_training_plan_text,
    validate_upload,
)

EXTRACTION_PROMPT = "Extract the training program text."


def _make_text_pdf(text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def _mock_openai_response(content: str) -> MagicMock:
    client = MagicMock()
    client.chat.completions.create.return_value.choices = [
        MagicMock(message=MagicMock(content=content))
    ]
    return client


def test_validate_upload_rejects_unsupported_mime():
    try:
        validate_upload(mime_type="text/plain", size_bytes=100)
        assert False, "expected UnsupportedMediaTypeError"
    except UnsupportedMediaTypeError as err:
        assert "text/plain" in str(err)


def test_validate_upload_rejects_oversized_file():
    try:
        validate_upload(mime_type="image/jpeg", size_bytes=11 * 1024 * 1024)
        assert False, "expected FileTooLargeError"
    except FileTooLargeError:
        pass


def test_pdf_text_layer_skips_vision():
    pdf = _make_text_pdf("Semaine 1\nJour 1 — Course 45 min\nJour 2 — Muscu")
    client = _mock_openai_response("should not be called")

    result = extract_training_plan_text(
        pdf,
        "application/pdf",
        client=client,
        extraction_prompt=EXTRACTION_PROMPT,
    )

    assert "Semaine 1" in result["extracted_text"]
    assert result["page_count"] == 1
    client.chat.completions.create.assert_not_called()


def test_image_uses_vision():
    client = _mock_openai_response("Lundi: 10 km\nMercredi: fractions")
    fake_jpeg = b"\xff\xd8\xff" + b"\x00" * 100

    result = extract_training_plan_text(
        fake_jpeg,
        "image/jpeg",
        client=client,
        extraction_prompt=EXTRACTION_PROMPT,
    )

    assert result["extracted_text"] == "Lundi: 10 km\nMercredi: fractions"
    client.chat.completions.create.assert_called_once()


def test_scanned_pdf_uses_vision_per_page():
    # Empty text layer → vision path
    pdf = _make_text_pdf(" ")
    client = _mock_openai_response("Page content")

    result = extract_training_plan_text(
        pdf,
        "application/pdf",
        client=client,
        extraction_prompt=EXTRACTION_PROMPT,
    )

    assert "Page content" in result["extracted_text"]
    assert client.chat.completions.create.call_count == 1


def test_empty_extraction_raises():
    client = _mock_openai_response("   ")
    try:
        extract_training_plan_text(
            b"\xff\xd8\xff" + b"\x00" * 50,
            "image/jpeg",
            client=client,
            extraction_prompt=EXTRACTION_PROMPT,
        )
        assert False, "expected EmptyExtractionError"
    except EmptyExtractionError:
        pass


def test_build_import_user_message():
    from planner import build_import_user_message  # noqa: E402

    msg = build_import_user_message("Run 5 km", "plan.pdf")
    assert "plan.pdf" in msg
    assert "Run 5 km" in msg
    assert "Propose un planning" in msg


def test_resolve_mime_type_from_magic_bytes():
    from document_import import resolve_mime_type  # noqa: E402

    assert resolve_mime_type(b"%PDF-1.4", "", "upload.bin") == "application/pdf"
    assert resolve_mime_type(b"\xff\xd8\xff\xab", "", "photo") == "image/jpeg"
    assert resolve_mime_type(b"\x89PNG\r\n\x1a\n", "", "x") == "image/png"
    assert resolve_mime_type(b"data", "image/jpg", "x.jpg") == "image/jpeg"
    assert resolve_mime_type(b"data", "", "plan.pdf") == "application/pdf"
