# Golden path (parity baseline)

Recorded during lightweight consolidation. Use the same prompt + prefs to regression-test after refactors.

## Inputs

- `rest_day`: Sunday
- `duration_min`: 60
- User message: `I want to run 3 times this week, with one long run on Saturday.`

## Expected server behavior

1. `calendar_busy_intervals(50)` → busy context in system prompt (or `[]` if calendar unavailable)
2. Chat streams plain-text plan (no JSON in first reply)
3. Schedule: last assistant message → convert prompt → JSON array → conflict filter → `add_sessions_to_calendar`

## Schedule result shape

```json
{
  "ok": true,
  "scheduled_count": <n>,
  "errors": [],
  "warnings": [],
  "conflicting_sessions": []
}
```

## Smoke (imports)

```bash
PYTHONPATH=src python3 -c "from planner import load_prompts, build_plain_text_system; print('ok')"
PYTHONPATH=src uvicorn server:app --host 127.0.0.1 --port 8000
curl http://127.0.0.1:8000/api/health
```
