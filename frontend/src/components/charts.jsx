import { Badge } from './ui.jsx'
import { signed } from '../utils.js'

const toneColor = (att) => (att >= 100 ? 'var(--green)' : att >= 90 ? '#d98b00' : 'var(--red)')

/** Up / down / flat indicator for a change in attainment points. */
export function TrendBadge({ trend, delta }) {
  const icon = trend === 'up' ? '▲' : trend === 'down' ? '▼' : '►'
  const tone = trend === 'up' ? 'ok' : trend === 'down' ? 'bad' : 'plain'
  return (
    <Badge tone={tone}>
      <span aria-hidden="true">{icon}</span> {signed(delta)} pts
      <span className="sr-only"> {trend === 'up' ? 'up' : trend === 'down' ? 'down' : 'flat'} versus last month</span>
    </Badge>
  )
}

export function Sparkline({ values, width = 110, height = 34 }) {
  if (!values.length) return null
  const lo = Math.min(...values, 90)
  const hi = Math.max(...values, 100)
  const x = (i) => (values.length === 1 ? width / 2 : (i / (values.length - 1)) * (width - 6) + 3)
  const y = (v) => height - 4 - ((v - lo) / (hi - lo || 1)) * (height - 8)
  const last = values[values.length - 1]
  return (
    <svg className="spark" width={width} height={height} viewBox={`0 0 ${width} ${height}`} role="img"
      aria-label={`Trend: ${values.map((v) => Math.round(v)).join(', ')} percent of target`}>
      <line x1="0" x2={width} y1={y(100)} y2={y(100)} stroke="#b4bfd6" strokeDasharray="3 3" />
      <polyline fill="none" stroke={toneColor(last)} strokeWidth="2" strokeLinejoin="round"
        points={values.map((v, i) => `${x(i)},${y(v)}`).join(' ')} />
      <circle cx={x(values.length - 1)} cy={y(last)} r="3" fill={toneColor(last)} />
    </svg>
  )
}

/** Bars of % of target per month, with the 100% line. */
export function AttainmentChart({ series, height = 150 }) {
  const W = 360
  const base = height - 26
  const max = Math.max(120, ...series.map((s) => s.attainment + 10))
  const y = (v) => base - (v / max) * (base - 14)
  const slot = W / series.length
  return (
    <svg className="chart" viewBox={`0 0 ${W} ${height}`} role="img"
      aria-label={`Percent of target by month: ${series.map((s) => `${s.label} ${Math.round(s.attainment)}`).join(', ')}`}>
      <line x1="0" x2={W} y1={y(100)} y2={y(100)} stroke="#9aa8c4" strokeDasharray="4 4" />
      <text x={W - 2} y={y(100) - 4} textAnchor="end" fontSize="9" fill="#66728f">target 100%</text>
      {series.map((s, i) => {
        const bw = Math.min(34, slot - 12)
        const bx = i * slot + (slot - bw) / 2
        return (
          <g key={s.month ?? s.label}>
            <rect x={bx} y={y(s.attainment)} width={bw} height={base - y(s.attainment)} rx="5"
              fill={toneColor(s.attainment)} opacity={i === series.length - 1 ? 1 : 0.55} />
            <text x={bx + bw / 2} y={y(s.attainment) - 5} textAnchor="middle" fontSize="10" fill="#25304f">
              {Math.round(s.attainment)}
            </text>
            <text x={bx + bw / 2} y={height - 8} textAnchor="middle" fontSize="10" fill="#66728f">{s.label}</text>
          </g>
        )
      })}
    </svg>
  )
}
