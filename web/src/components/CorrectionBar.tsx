import { useState } from 'react'
import { postCorrection } from '../lib/api'
import type { Summary, Video } from '../lib/types'

interface Props {
  video: Video
  summary: Summary | null
  /** The span dragged out on the timeline, in seconds, or null. */
  span: [number, number] | null
  onClear(): void
}

/**
 * Telling the fly it was wrong, and where.
 *
 * A video the fly met in the wild and got wrong is the most valuable labelled
 * example this project can obtain: it is out of distribution, a human found
 * it, and the exact seconds are known. Everything submitted here lands in
 * `data/corrections.jsonl` as an append-only log, which `frrf-corrections`
 * folds back into training.
 */
export default function CorrectionBar({ video, summary, span, onClear }: Props) {
  const [note, setNote] = useState('')
  const [state, setState] = useState<'idle' | 'sending' | 'saved' | 'failed'>('idle')
  const [error, setError] = useState<string | null>(null)

  const send = async (label: 'rickroll' | 'not-rickroll') => {
    if (!span) return
    setState('sending')
    setError(null)
    try {
      await postCorrection({
        videoId: video.id,
        label,
        start: span[0],
        end: span[1],
        title: video.title,
        url: video.watchUrl,
        note,
        verdictWas: summary?.verdict ?? null,
        committedAt: summary?.committedAt ?? null,
      })
      setState('saved')
      setNote('')
      onClear()
      window.setTimeout(() => setState('idle'), 2600)
    } catch (problem) {
      setState('failed')
      setError(problem instanceof Error ? problem.message : String(problem))
    }
  }

  if (!span) {
    return (
      <p className="correction-hint">
        {state === 'saved'
          ? 'saved — thank you, that is training data now'
          : 'wrong? drag across the response above to mark where the song actually is'}
      </p>
    )
  }

  return (
    <div className="correction">
      <span className="correction-span">
        {span[0].toFixed(1)}s – {span[1].toFixed(1)}s
      </span>
      <input
        className="correction-note"
        placeholder="what is in this span? (optional)"
        value={note}
        onChange={(event) => setNote(event.target.value)}
        maxLength={200}
      />
      <button
        type="button"
        className="chip chip-yes"
        disabled={state === 'sending'}
        onClick={() => send('rickroll')}
      >
        this is the song
      </button>
      <button
        type="button"
        className="chip"
        disabled={state === 'sending'}
        onClick={() => send('not-rickroll')}
      >
        this is not
      </button>
      <button type="button" className="chip chip-quiet" onClick={onClear}>
        cancel
      </button>
      {error && <span className="correction-error">{error}</span>}
    </div>
  )
}
