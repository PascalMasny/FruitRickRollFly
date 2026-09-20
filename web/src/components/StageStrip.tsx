import type { Stage } from '../lib/types'

const STEPS: { key: Stage; label: string }[] = [
  { key: 'resolving', label: 'resolving the link' },
  { key: 'fetching', label: 'fetching the audio' },
  { key: 'hearing', label: 'hearing it' },
  { key: 'judging', label: 'running the circuit' },
  { key: 'done', label: 'done' },
]

export default function StageStrip({ stage, error }: { stage: Stage | 'idle'; error: string | null }) {
  if (stage === 'idle') return null
  if (stage === 'failed') return <div className="stage-strip stage-failed">{error ?? 'failed'}</div>

  const index = STEPS.findIndex((step) => step.key === stage)
  return (
    <ol className="stage-strip">
      {STEPS.map((step, i) => (
        <li
          key={step.key}
          className={i < index ? 'done' : i === index ? 'current' : 'pending'}
        >
          {step.label}
        </li>
      ))}
    </ol>
  )
}
