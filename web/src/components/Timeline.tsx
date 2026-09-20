import type { Frame, Summary } from '../lib/types'

interface Props {
  frames: Frame[]
  summary: Summary | null
  at: number
  commitThreshold: number
  onSeek(seconds: number): void
}

const W = 1000
const H = 120

function path(frames: Frame[], pick: (f: Frame) => number, span: number): string {
  if (frames.length === 0) return ''
  const last = frames[frames.length - 1]?.t || 1
  const points = frames.map((frame) => {
    if (!frame) return null
    const x = (frame.t / last) * W
    const y = H - Math.max(0, Math.min(1, pick(frame) / span)) * H
    return `${x.toFixed(1)},${y.toFixed(1)}`
  })
  return `M ${points.filter(Boolean).join(' L ')}`
}

/**
 * The whole response on one strip: confidence behind, dopamine in front.
 *
 * Clicking it seeks, so the video and the fly stay locked together whichever
 * one you drive.
 */
export default function Timeline({ frames, summary, at, commitThreshold, onSeek }: Props) {
  const dense = frames.filter(Boolean)
  if (dense.length === 0) return null
  const duration = dense[dense.length - 1].t

  return (
    <div className="timeline">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        preserveAspectRatio="none"
        onClick={(event) => {
          const box = event.currentTarget.getBoundingClientRect()
          onSeek(((event.clientX - box.left) / box.width) * duration)
        }}
        role="slider"
        aria-label="Response timeline; click to seek"
        aria-valuemin={0}
        aria-valuemax={duration}
        aria-valuenow={at}
        tabIndex={0}
      >
        <line x1="0" y1={H / 2} x2={W} y2={H / 2} className="tl-grid" />
        <line
          x1="0"
          y1={H - commitThreshold * H}
          x2={W}
          y2={H - commitThreshold * H}
          className="tl-threshold"
        />
        <path d={path(dense, (f) => f.confidence, 1)} className="tl-confidence" />
        <path d={path(dense, (f) => f.dopamine, 1)} className="tl-dopamine" />
        <path d={path(dense, (f) => f.aversion, 1)} className="tl-aversion" />
        {summary?.committedAt != null && (
          <line
            x1={(summary.committedAt / duration) * W}
            y1="0"
            x2={(summary.committedAt / duration) * W}
            y2={H}
            className="tl-commit"
          />
        )}
        <line
          x1={(at / duration) * W}
          y1="0"
          x2={(at / duration) * W}
          y2={H}
          className="tl-playhead"
        />
      </svg>
      <div className="timeline-legend">
        <span className="key key-confidence">confidence</span>
        <span className="key key-dopamine">dopamine</span>
        <span className="key key-aversion">aversion</span>
        <span className="key key-threshold">commit threshold</span>
        <span className="timeline-clock">
          {at.toFixed(1)} s / {duration.toFixed(0)} s
        </span>
      </div>
    </div>
  )
}
