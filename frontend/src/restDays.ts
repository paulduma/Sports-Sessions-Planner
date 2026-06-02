export const WEEKDAYS = [
  'Monday',
  'Tuesday',
  'Wednesday',
  'Thursday',
  'Friday',
  'Saturday',
  'Sunday',
] as const

export type Weekday = (typeof WEEKDAYS)[number]

export const WEEKDAY_LABEL_FR: Record<Weekday, string> = {
  Monday: 'Lundi',
  Tuesday: 'Mardi',
  Wednesday: 'Mercredi',
  Thursday: 'Jeudi',
  Friday: 'Vendredi',
  Saturday: 'Samedi',
  Sunday: 'Dimanche',
}

export function weekdayLabelFr(day: string): string {
  return WEEKDAY_LABEL_FR[day as Weekday] ?? day
}

/** Stable order for API / prompt (Monday → Sunday). */
export function sortRestDays(days: string[]): string[] {
  const order = new Map<string, number>(
    WEEKDAYS.map((d, i) => [d, i]),
  )
  return [...days].sort(
    (a, b) => (order.get(a) ?? 99) - (order.get(b) ?? 99),
  )
}

/** Value sent as `rest_day` to the API (unchanged field name). */
export function formatRestDaysForApi(days: string[]): string {
  const sorted = sortRestDays(days)
  if (sorted.length === 0) return 'Aucun'
  return sorted.map(weekdayLabelFr).join(', ')
}

/** Short label for sidebar / dropdown summary. */
export function formatRestDaysLabel(
  days: string[],
  emptyLabel = 'Aucun',
): string {
  const sorted = sortRestDays(days)
  if (sorted.length === 0) return emptyLabel
  return sorted.map(weekdayLabelFr).join(', ')
}
