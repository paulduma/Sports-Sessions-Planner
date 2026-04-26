export type ApiMessage = { role: 'user' | 'agent'; content: string }

export type ScheduleResult = {
  ok: boolean
  scheduled_count: number
  errors: string[]
  warnings: string[]
  conflicting_sessions: Record<string, unknown>[]
}

type SsePayload =
  | { type: 'delta'; delta: string }
  | { type: 'done' }
  | { type: 'error'; message: string }

const API_OFFLINE_HINT =
  'Cannot reach API server. Start backend with: PYTHONPATH=src uvicorn api.main:app --reload --host 127.0.0.1 --port 8000'

function parseSseBlocks(buffer: string): { events: SsePayload[]; rest: string } {
  const events: SsePayload[] = []
  let rest = buffer
  while (true) {
    const sep = rest.indexOf('\n\n')
    if (sep < 0) break
    const block = rest.slice(0, sep)
    rest = rest.slice(sep + 2)
    for (const line of block.split('\n')) {
      const trimmed = line.trim()
      if (!trimmed.startsWith('data:')) continue
      const jsonStr = trimmed.slice(5).trim()
      try {
        events.push(JSON.parse(jsonStr) as SsePayload)
      } catch {
        // ignore malformed chunk
      }
    }
  }
  return { events, rest }
}

export async function streamChatCompletion(
  messages: ApiMessage[],
  restDay: string,
  durationMin: number,
  onDelta: (chunk: string) => void,
): Promise<void> {
  let res: Response
  try {
    res = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        messages,
        rest_day: restDay,
        duration_min: durationMin,
      }),
    })
  } catch (err) {
    // Fetch throws TypeError on network failures (API down / proxy target unreachable).
    throw new Error(
      err instanceof Error && err.message ? `${API_OFFLINE_HINT} (${err.message})` : API_OFFLINE_HINT,
    )
  }

  if (!res.ok || !res.body) {
    const text = await res.text().catch(() => '')
    throw new Error(text || `Chat request failed (${res.status})`)
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const { events, rest } = parseSseBlocks(buffer)
    buffer = rest
    for (const ev of events) {
      if (ev.type === 'delta' && ev.delta) onDelta(ev.delta)
      if (ev.type === 'error') throw new Error(ev.message)
    }
  }

  const { events: tailEvents } = parseSseBlocks(buffer + '\n\n')
  for (const ev of tailEvents) {
    if (ev.type === 'delta' && ev.delta) onDelta(ev.delta)
    if (ev.type === 'error') throw new Error(ev.message)
  }
}

export async function scheduleSessions(
  messages: ApiMessage[],
  restDay: string,
  durationMin: number,
): Promise<ScheduleResult> {
  let res: Response
  try {
    res = await fetch('/api/schedule', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        messages,
        rest_day: restDay,
        duration_min: durationMin,
      }),
    })
  } catch (err) {
    throw new Error(
      err instanceof Error && err.message ? `${API_OFFLINE_HINT} (${err.message})` : API_OFFLINE_HINT,
    )
  }
  const data = (await res.json().catch(() => ({}))) as
    | ScheduleResult
    | { detail?: unknown }
  if (!res.ok) {
    const detail =
      'detail' in data && data.detail !== undefined
        ? JSON.stringify(data.detail)
        : JSON.stringify(data)
    throw new Error(detail || `Schedule failed (${res.status})`)
  }
  return data as ScheduleResult
}
