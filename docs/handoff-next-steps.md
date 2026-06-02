# Sports Sessions Planner — Handoff (juin 2026)

Projet : `/Users/Paul/Desktop/Apps Projects/Sports-Sessions-Planner`

Chatbot coach sportif : lit Google Calendar → propose un plan texte → convertit en JSON → écrit les séances dans Calendar.

---

## Démarrer l'app

```bash
# Terminal 1 — API (sans proxy si erreur OpenAI)
cd "/Users/Paul/Desktop/Apps Projects/Sports-Sessions-Planner"
source venv/bin/activate
unset HTTP_PROXY HTTPS_PROXY ALL_PROXY http_proxy https_proxy all_proxy
export NO_PROXY="localhost,127.0.0.1,api.openai.com,.openai.com"
PYTHONPATH=src uvicorn server:app --reload --host 127.0.0.1 --port 8000

# Terminal 2 — Frontend
cd frontend && npm run dev
# → http://localhost:5173
```

Prérequis : `.env` (`OPENAI_API_KEY`), `credentials/credentials.json`, `credentials/token.json`.

Port 8000 occupé : `lsof -ti:8000 | xargs kill`

---

## Architecture (post-consolidation)

```
src/
  planner.py           # OpenAI chat + schedule + conflicts
  google_calendar.py   # OAuth, list events, create events
  config.yaml          # Prompts coach
  server.py            # FastAPI : /api/health, /api/calendar/status, /api/chat/stream, /api/schedule
frontend/              # React + Vite (proxy /api → :8000)
```

---

## Tests manuels — Résultats (tous OK fonctionnellement)

| # | Test | Résultat |
|---|------|----------|
| 1 | Google retrieve (`list_upcoming_events`) | OK — sidebar « connecté » |
| 2 | OpenAI chat (streaming SSE) | OK — après `unset` proxy + redémarrage API |
| 3 | Prompt / choix créneaux | OK contenu — plan cohérent (dates, heures, 3 séances) |
| 4 | Edit agenda (`add_sessions_to_calendar`) | OK — « Valider et planifier » crée les events |

Golden path : `docs/golden-path.md`

---

## Gaps identifiés (backlog priorisé)

### P1 — UX chat (test 3)

**Symptômes :** `**markdown**` affiché en brut ; long plan chevauche la barre fixe (input + bouton planifier).

**Cause :**
- `frontend/src/components/MessageBubble.tsx` — `{message.content}` texte plain, pas de rendu markdown
- `frontend/src/components/ChatArea.tsx` — scroll `pb-32` insuffisant ; footer `absolute` empile bouton + input

**Fix suggéré :**
- U1 : `react-markdown` + `prose` (ou `whitespace-pre-wrap` minimum) dans `MessageBubble.tsx`
- U2 : `pb-48`/`pb-56` ou padding dynamique (ref footer + `ResizeObserver`) dans `ChatArea.tsx`
- U3 (optionnel) : bouton « Valider et planifier » sous le dernier message (dans la zone scroll)
- U4 : renforcer `config.yaml` (« no asterisks, one session per line ») ou accepter markdown côté UI

### P2 — Multi-calendrier (agenda pro)

**Symptôme :** lit `primary` uniquement, pas l'agenda pro lié au même compte Google.

**Cause :** `google_calendar.py` — `calendar_id="primary"` en dur dans `list_upcoming_events` et `add_sessions_to_calendar`.

**Fix suggéré :**
- `GOOGLE_CALENDAR_IDS=primary,<work-calendar-id>` (env)
- `calendarList.list()` + fusion events pour `busy_context`
- `GOOGLE_WRITE_CALENDAR_ID` pour l'écriture
- Sidebar : afficher quels calendriers sont lus

### P3 — Doc / ops

- README : commande `unset` proxy, `cd frontend` pour npm, multi-calendrier
- Éviter `500` opaque si le générateur SSE chat échoue avant le 1er yield (`server.py`)

---

## Mapping libellés → code

| Besoin | Code |
|--------|------|
| Lire agenda | `calendar_busy_intervals()` → `list_upcoming_events()` |
| Chat | `POST /api/chat/stream` → `stream_chat_completion()` |
| Plan / créneaux | `build_plain_text_system()` + `config.yaml` |
| Écrire agenda | `POST /api/schedule` → `schedule_from_last_assistant()` → `add_sessions_to_calendar()` |

---

## Prochaine session recommandée

1. Implémenter **P1** (U1 + U2) — quick win UX
2. Puis **P2** multi-calendrier pro
3. Mettre à jour README (**P3**)

Ne pas toucher à la logique métier dans `planner.py` sauf si multi-calendrier impacte `calendar_busy_intervals`.
