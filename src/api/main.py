from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# Ensure `src` is importable when running: uvicorn api.main:app
_SRC = Path(__file__).resolve().parents[1]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

load_dotenv(_SRC.parent / ".env")

from app.chat_service import (  # noqa: E402
    build_plain_text_system,
    busy_context_string,
    calendar_busy_intervals,
    load_prompts,
    openai_client,
    schedule_from_last_assistant,
    stream_chat_completion,
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


@app.get("/api/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/api/calendar/status")
def calendar_status() -> Dict[str, Any]:
    """Probe Google Calendar read access (same path as planning)."""
    try:
        from app.calendar import list_upcoming_events

        upcoming = list_upcoming_events(max_results=1)
        return {"connected": True, "busy_sample_count": len(upcoming or [])}
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
        intervals = calendar_busy_intervals(max_results=50)
        busy_ctx = busy_context_string(intervals)
        system_prompt = build_plain_text_system(
            prompts,
            today_str=today_str,
            rest_day=body.rest_day,
            duration_min=body.duration_min,
            busy_context=busy_ctx,
        )
        client = openai_client()
        model = body.model or _default_model()
        conv = [{"role": m.role, "content": m.content} for m in body.messages]
    except Exception as err:
        def init_error_gen():
            yield _sse_data({"type": "error", "message": f"Chat initialization failed: {err}"})
        return StreamingResponse(init_error_gen(), media_type="text/event-stream")

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
