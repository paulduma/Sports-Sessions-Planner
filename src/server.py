"""Thin FastAPI HTTP adapter for the sports planner."""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from openai import APIConnectionError, APIStatusError
from pydantic import BaseModel, Field

_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

load_dotenv(_SRC.parent / ".env")

from planner import (  # noqa: E402
    build_import_user_message,
    build_plain_text_system,
    busy_context_string,
    calendar_busy_intervals,
    events_to_busy_intervals,
    fetch_calendar_events,
    load_prompts,
    openai_client,
    schedule_from_last_assistant,
    stream_chat_completion,
    upcoming_events_context_string,
)

app = FastAPI(title="Sports Sessions Planner API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "agent", "system"]
    content: str


class ChatStreamRequest(BaseModel):
    messages: List[ChatMessage] = Field(default_factory=list)
    rest_day: str = "None"
    duration_min: int = 60
    model: Optional[str] = None


class ScheduleRequest(BaseModel):
    messages: List[ChatMessage] = Field(default_factory=list)
    rest_day: str = "None"
    duration_min: int = 60
    model: Optional[str] = None


def _default_model() -> str:
    return "gpt-3.5-turbo"


def _sse_data(obj: Dict[str, Any]) -> str:
    return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"


def _sse_error_stream(message: str) -> StreamingResponse:
    """Return HTTP 200 SSE with a structured error (avoids opaque 500 before first yield)."""

    def gen():
        yield _sse_data({"type": "error", "message": message})

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/api/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/api/calendar/status")
def calendar_status() -> Dict[str, Any]:
    try:
        from google_calendar import calendar_connection_status

        return calendar_connection_status(max_results=1)
    except FileNotFoundError as err:
        return {"connected": False, "error": str(err)}
    except Exception as err:
        return {"connected": False, "error": str(err)}


@app.post("/api/chat/stream")
def chat_stream(body: ChatStreamRequest):
    if not body.messages:
        raise HTTPException(status_code=400, detail="messages must not be empty")

    last = body.messages[-1]
    if last.role not in ("user",):
        raise HTTPException(status_code=400, detail="last message must be from user")

    try:
        prompts = load_prompts()
        today_str = date.today().isoformat()
        calendar_events = fetch_calendar_events(max_results=50)
        busy_ctx = busy_context_string(events_to_busy_intervals(calendar_events))
        upcoming_ctx = upcoming_events_context_string(calendar_events)
        system_prompt = build_plain_text_system(
            prompts,
            today_str=today_str,
            rest_day=body.rest_day,
            duration_min=body.duration_min,
            busy_context=busy_ctx,
            upcoming_events=upcoming_ctx,
        )
        client = openai_client()
        model = body.model or _default_model()
        conv = [{"role": m.role, "content": m.content} for m in body.messages]
    except Exception as err:
        return _sse_error_stream(f"Chat initialization failed: {err}")

    def gen():
        try:
            for delta in stream_chat_completion(
                client=client,
                model=model,
                system_prompt=system_prompt,
                conversation=conv,
            ):
                if delta:
                    yield _sse_data({"type": "delta", "delta": delta})
            yield _sse_data({"type": "done"})
        except Exception as err:
            yield _sse_data({"type": "error", "message": str(err)})

    return StreamingResponse(gen(), media_type="text/event-stream")


def _document_import_module():
    try:
        import document_import
    except ImportError as err:
        raise HTTPException(
            status_code=503,
            detail=(
                "Dépendance pymupdf manquante dans ce Python. "
                "Lance l'API avec : ./scripts/start-api.sh "
                "(ou : source venv/bin/activate && pip install -r requirements.txt). "
                f"Détail : {err}"
            ),
        ) from err
    return document_import


@app.post("/api/import/extract")
async def import_extract(file: UploadFile = File(...)) -> Dict[str, Any]:
    raw = await file.read()
    filename = file.filename or "upload"
    doc = _document_import_module()
    mime = doc.resolve_mime_type(raw, file.content_type, filename)

    try:
        prompts = load_prompts()
        extraction_prompt = prompts.get("import_extraction_prompt", "").strip()
        if not extraction_prompt:
            raise HTTPException(status_code=500, detail="import_extraction_prompt not configured")

        result = doc.extract_training_plan_text(
            raw,
            mime,
            client=openai_client(),
            extraction_prompt=extraction_prompt,
        )
        return {
            "extracted_text": result["extracted_text"],
            "source_filename": filename,
            **({"page_count": result["page_count"]} if "page_count" in result else {}),
            "user_message": build_import_user_message(result["extracted_text"], filename),
        }
    except doc.UnsupportedMediaTypeError as err:
        raise HTTPException(status_code=415, detail=str(err)) from err
    except doc.FileTooLargeError as err:
        raise HTTPException(status_code=413, detail=str(err)) from err
    except doc.EmptyExtractionError as err:
        raise HTTPException(status_code=422, detail=str(err)) from err
    except APIConnectionError as err:
        raise HTTPException(
            status_code=502,
            detail=(
                "Connexion OpenAI impossible. Vérifie OPENAI_API_KEY et relance l'API "
                "sans proxy (unset HTTP_PROXY HTTPS_PROXY)."
            ),
        ) from err
    except APIStatusError as err:
        raise HTTPException(
            status_code=502,
            detail=f"OpenAI a refusé l'analyse : {err.message}",
        ) from err
    except HTTPException:
        raise
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {err}") from err


@app.post("/api/schedule")
def schedule(body: ScheduleRequest) -> Dict[str, Any]:
    last_assistant: Optional[str] = None
    for m in reversed(body.messages):
        if m.role in ("assistant", "agent") and m.content.strip():
            last_assistant = m.content
            break
    if not last_assistant:
        raise HTTPException(status_code=400, detail="No assistant reply to validate.")

    intervals = calendar_busy_intervals(max_results=50)
    busy_ctx = busy_context_string(intervals)
    client = openai_client()
    model = body.model or _default_model()

    return schedule_from_last_assistant(
        client=client,
        model=model,
        last_assistant_plain=last_assistant,
        busy_context=busy_ctx,
    )
