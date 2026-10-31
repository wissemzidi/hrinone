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
