#!/usr/bin/env python3
"""Tests for POST /api/import/extract."""

import sys
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import fitz
from fastapi.testclient import TestClient

_SRC = Path(__file__).resolve().parents[1]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from server import app  # noqa: E402

client = TestClient(app)


def _text_pdf_bytes(text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    data = doc.tobytes()
    doc.close()
    return data


def test_import_extract_rejects_txt():
    res = client.post(
        "/api/import/extract",
        files={"file": ("plan.txt", b"hello", "text/plain")},
    )
    assert res.status_code == 415


@patch("server.openai_client")
@patch("server.load_prompts")
def test_import_extract_pdf_text_layer(mock_load_prompts, mock_openai_client):
    mock_load_prompts.return_value = {"import_extraction_prompt": "Extract text."}
    mock_openai_client.return_value = object()

    pdf = _text_pdf_bytes("Semaine 1 — Endurance\nMardi: 8 km facile")
    res = client.post(
        "/api/import/extract",
        files={"file": ("plan.pdf", pdf, "application/pdf")},
    )

    assert res.status_code == 200
    body = res.json()
    assert "Semaine 1" in body["extracted_text"]
    assert body["source_filename"] == "plan.pdf"
    assert "user_message" in body
    assert "plan.pdf" in body["user_message"]
