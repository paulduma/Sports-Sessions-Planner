import { useEffect, useState } from 'react'
import {
  CheckCircleIcon,
  ActivityIcon,
  PlusIcon,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react'

const edgeToggleClass =
  'absolute -right-3 top-1/2 z-10 flex h-6 w-6 -translate-y-1/2 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-600 shadow-sm transition-colors hover:bg-slate-50 hover:text-slate-900'

const REST_DAYS = [
  'None',
  'Monday',
  'Tuesday',
  'Wednesday',
  'Thursday',
  'Friday',
  'Saturday',
  'Sunday',
] as const

type CalendarInfo = {
  id: string
  summary: string
  read: boolean
  write: boolean
}

type CalendarStatus = {
  connected?: boolean
  calendars?: CalendarInfo[]
  error?: string
}

interface SidebarProps {
  onNewChat: () => void
  restDay: string
  setRestDay: (value: string) => void
  durationMin: number
  setDurationMin: (value: number) => void
}

export function Sidebar({
  onNewChat,
  restDay,
  setRestDay,
  durationMin,
  setDurationMin,
}: SidebarProps) {
  const [collapsed, setCollapsed] = useState(false)
  const [calendarStatus, setCalendarStatus] = useState<CalendarStatus | null>(
    null,
  )

  useEffect(() => {
    let cancelled = false
    fetch('/api/calendar/status')
      .then((r) => r.json())
      .then((body: CalendarStatus) => {
        if (!cancelled) setCalendarStatus(body)
      })
      .catch(() => {
        if (!cancelled) setCalendarStatus({ connected: false })
      })
    return () => {
      cancelled = true
    }
  }, [])

  const calendarOk = calendarStatus?.connected ?? null
  const readCalendars =
    calendarStatus?.calendars?.filter((c) => c.read) ?? []

  if (collapsed) {
    return (
      <div className="relative hidden h-full w-3 flex-shrink-0 border-r border-slate-200 bg-[#F1F5F9] md:block">
        <button
          type="button"
          onClick={() => setCollapsed(false)}
          aria-label="Ouvrir le menu"
          title="Ouvrir le menu"
          className={edgeToggleClass}
        >
          <ChevronRight size={14} />
        </button>
      </div>
    )
  }

  return (
    <div className="relative hidden h-full w-[260px] flex-shrink-0 flex-col justify-between border-r border-slate-200 bg-[#F1F5F9] p-4 md:flex">
      <button
        type="button"
        onClick={() => setCollapsed(true)}
        aria-label="Réduire le menu"
        title="Réduire le menu"
        className={edgeToggleClass}
      >
        <ChevronLeft size={14} />
      </button>
      <div>
        <div className="mb-6 flex items-center gap-3 px-2 py-4">
          <div className="rounded-lg bg-[#1E3A5F] p-1.5 text-white shadow-sm">
            <ActivityIcon size={20} className="stroke-[2.5]" />
          </div>
          <span className="text-lg font-bold leading-snug tracking-tight text-slate-900">
            Sports Planner Perso
          </span>
        </div>

        <button
          type="button"
          onClick={onNewChat}
          className="mb-6 flex w-full items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm font-medium text-slate-700 shadow-sm transition-colors hover:bg-slate-50"
        >
          <PlusIcon size={16} />
          Nouvelle discussion
        </button>

        <div className="mt-2 space-y-4 border-t border-slate-200/80 pt-6">
          <p className="px-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
            Préférences
          </p>
          <label className="block px-1 text-xs font-medium text-slate-600">
            Jour de repos
            <select
              value={restDay}
              onChange={(e) => setRestDay(e.target.value)}
              className="mt-1.5 w-full rounded-lg border border-slate-200 bg-white px-2 py-2 text-sm text-slate-800 shadow-sm"
            >
              {REST_DAYS.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
          </label>
          <label className="block px-1 text-xs font-medium text-slate-600">
            Durée typique (min): {durationMin}
            <input
              type="range"
              min={20}
              max={150}
              step={10}
              value={durationMin}
              onChange={(e) => setDurationMin(Number(e.target.value))}
              className="mt-2 w-full accent-[#1E3A5F]"
            />
          </label>
        </div>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white px-3 py-3 shadow-sm">
        <div className="flex items-center gap-3">
          <div
            className={`rounded-full p-1 ${calendarOk ? 'bg-emerald-50 text-emerald-600' : calendarOk === false ? 'bg-slate-100 text-slate-400' : 'bg-slate-100 text-slate-400'}`}
          >
            <CheckCircleIcon size={14} />
          </div>
          <div className="min-w-0 flex-1">
            <span className="text-xs font-medium text-slate-800">
              Google Calendar
            </span>
            <p className="text-[10px] text-slate-400">
              {calendarOk === null
                ? 'Vérification…'
                : calendarOk
                  ? 'Synchronisé'
                  : 'Hors ligne ou non connecté'}
            </p>
          </div>
        </div>

        {calendarOk && readCalendars.length > 0 ? (
          <ul className="mt-2 space-y-1 border-t border-slate-100 pt-2">
            {readCalendars.map((cal) => (
              <li
                key={cal.id}
                className="truncate text-[10px] text-slate-500"
                title={cal.id}
              >
                <span className="font-medium text-slate-600">
                  {cal.summary}
                </span>
                {cal.write ? ' · écriture' : ' · lecture'}
              </li>
            ))}
          </ul>
        ) : null}
      </div>
    </div>
  )
}
