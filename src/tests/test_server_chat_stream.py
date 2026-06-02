#!/usr/bin/env python3
"""Verify chat SSE returns structured errors instead of opaque HTTP 500."""

import json
import sys
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

_SRC = Path(__file__).resolve().parents[1]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from server import app  # noqa: E402

client = TestClient(app)

CHAT_BODY = {"messages": [{"role": "user", "content": "Plan 3 runs this week"}]}


def _parse_sse_events(text: str) -> list[dict]:
    events = []
    for block in text.split("\n\n"):
        for line in block.split("\n"):
            line = line.strip()
            if not line.startswith("data:"):
                continue
            events.append(json.loads(line[5:].strip()))
    return events


def _mock_init_dependencies():
    return patch.multiple(
        "server",
        load_prompts=lambda: {},
        calendar_busy_intervals=lambda max_results=50: [],
        busy_context_string=lambda intervals: "",
        build_plain_text_system=lambda *args, **kwargs: "system",
        openai_client=lambda: object(),
    )


def test_chat_stream_init_failure_returns_sse_error():
    with _mock_init_dependencies():
        with patch("server.openai_client", side_effect=RuntimeError("missing API key")):
            res = client.post("/api/chat/stream", json=CHAT_BODY)

    assert res.status_code == 200
    assert "text/event-stream" in res.headers.get("content-type", "")
    events = _parse_sse_events(res.text)
    assert any(ev.get("type") == "error" for ev in events)
    assert "missing API key" in events[-1]["message"]


def test_chat_stream_generator_failure_returns_sse_error():
    def failing_stream(*args, **kwargs):
        raise RuntimeError("OpenAI unreachable")
        yield ""  # pragma: no cover

    with _mock_init_dependencies():
        with patch("server.stream_chat_completion", side_effect=failing_stream):
            res = client.post("/api/chat/stream", json=CHAT_BODY)

    assert res.status_code == 200
    events = _parse_sse_events(res.text)
    assert any(ev.get("type") == "error" for ev in events)
    assert "OpenAI unreachable" in events[-1]["message"]


def test_chat_stream_empty_messages_returns_400():
    res = client.post("/api/chat/stream", json={"messages": []})
    assert res.status_code == 400
