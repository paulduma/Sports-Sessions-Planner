import { useEffect, useState, type ReactNode } from 'react'
import {
  MessageSquareIcon,
  CalendarIcon,
  SettingsIcon,
  CheckCircleIcon,
  ActivityIcon,
  PlusIcon,
} from 'lucide-react'

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
  const [calendarOk, setCalendarOk] = useState<boolean | null>(null)

  useEffect(() => {
    let cancelled = false
    fetch('/api/calendar/status')
      .then((r) => r.json())
      .then((body: { connected?: boolean }) => {
        if (!cancelled) setCalendarOk(Boolean(body.connected))
      })
      .catch(() => {
        if (!cancelled) setCalendarOk(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div className="hidden h-full w-[260px] flex-shrink-0 flex-col justify-between border-r border-slate-200 bg-[#F1F5F9] p-4 md:flex">
      <div>
        <div className="mb-6 flex items-center gap-3 px-2 py-4">
          <div className="rounded-lg bg-[#1E3A5F] p-1.5 text-white shadow-sm">
            <ActivityIcon size={20} className="stroke-[2.5]" />
          </div>
          <span className="text-lg font-bold tracking-tight text-slate-900">
            FitPlan AI
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

        <nav className="space-y-1">
          <NavItem icon={<MessageSquareIcon size={18} />} label="Chat" active />
          <NavItem icon={<CalendarIcon size={18} />} label="Agenda" />
          <NavItem icon={<SettingsIcon size={18} />} label="Paramètres" />
        </nav>

        <div className="mt-8 space-y-4 border-t border-slate-200/80 pt-6">
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

      <div className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white px-3 py-3 shadow-sm">
        <div className="rounded-full bg-emerald-50 p-1 text-emerald-600">
          <CheckCircleIcon size={14} />
        </div>
        <div className="flex flex-col">
          <span className="text-xs font-medium text-slate-800">
            Google Calendar
          </span>
          <span className="text-[10px] text-slate-400">
            {calendarOk === null
              ? 'Vérification…'
              : calendarOk
                ? 'Synchronisé'
                : 'Hors ligne ou non connecté'}
          </span>
        </div>
      </div>
    </div>
  )
}

function NavItem({
  icon,
  label,
  active = false,
}: {
  icon: ReactNode
  label: string
  active?: boolean
}) {
  return (
    <button
      type="button"
      className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${active ? 'border border-slate-200 bg-white text-[#1E3A5F] shadow-sm' : 'text-slate-500 hover:bg-white/60 hover:text-slate-700'}`}
    >
      {icon}
      {label}
    </button>
  )
}
