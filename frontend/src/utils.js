export const fullName = (p) => `${p.first_name} ${p.last_name}`

export const fmtDate = (iso) =>
  new Date(iso + 'T00:00:00').toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })

export function fmtRange(start, end) {
  return start === end ? fmtDate(start) : `${fmtDate(start)} – ${fmtDate(end)}`
}

export function countDays(start, end) {
  const ms = new Date(end + 'T00:00:00') - new Date(start + 'T00:00:00')
  return Math.round(ms / 86400000) + 1
}

export const LEAVE_TYPES = {
  vacation: 'Vacation',
  sick: 'Sick leave',
  personal: 'Personal',
  parental: 'Parental',
}

export const todayISO = () => new Date().toLocaleDateString('en-CA')

export function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

export const scoreTone = (score) => (score >= 75 ? 'ok' : score >= 50 ? 'warn' : 'bad')

export const STATUS_LABEL = { on_track: 'On track', watch: 'Watch', off_track: 'Off track' }
export const STATUS_TONE = { on_track: 'ok', watch: 'warn', off_track: 'bad' }
export const VALUE_LABEL = { adding_value: 'Adding value', borderline: 'Borderline', not_adding_value: 'Not adding value yet' }
export const VALUE_TONE = { adding_value: 'ok', borderline: 'warn', not_adding_value: 'bad' }

export const pct = (x, digits = 1) => (x == null ? '–' : `${(x * 100).toFixed(digits)}%`)
export const signed = (n) => `${n > 0 ? '+' : ''}${n.toFixed(1)}`

export const TRAINING_LABEL = { assigned: 'Upcoming', completed: 'Completed', overdue: 'Overdue', missed: 'Missed' }
export const TRAINING_TONE = { assigned: 'plain', completed: 'ok', overdue: 'warn', missed: 'bad' }

export const timeAgo = (iso) => {
  const s = Math.max(0, (Date.now() - new Date(iso.endsWith('Z') ? iso : iso + 'Z').getTime()) / 1000)
  if (s < 60) return 'just now'
  if (s < 3600) return `${Math.floor(s / 60)} min ago`
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`
  return `${Math.floor(s / 86400)} d ago`
}
