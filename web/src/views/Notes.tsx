import { useEffect, useRef, useState } from 'react'
import { fetchNotes, saveNotes } from '../lib/api'

/**
 * Somewhere to write things down, saved to `data/notes.md`.
 *
 * A file on disk rather than browser storage, because a research note that
 * only exists in one browser profile is a note that is going to be lost, and
 * because a file can be committed next to the code it is about.
 */
export default function Notes() {
  const [text, setText] = useState<string | null>(null)
  const [state, setState] = useState<'idle' | 'saving' | 'saved' | 'failed'>('idle')
  const timer = useRef<number | null>(null)

  useEffect(() => {
    fetchNotes()
      .then(setText)
      .catch(() => setText('# Research notes\n'))
    return () => {
      if (timer.current) window.clearTimeout(timer.current)
    }
  }, [])

  const change = (next: string) => {
    setText(next)
    setState('saving')
    // Debounced: a note is typed, and a write per keystroke is a write per
    // keystroke.
    if (timer.current) window.clearTimeout(timer.current)
    timer.current = window.setTimeout(() => {
      saveNotes(next)
        .then(() => setState('saved'))
        .catch(() => setState('failed'))
    }, 700)
  }

  if (text === null) {
    return (
      <div className="page">
        <p className="hint">opening the notebook…</p>
      </div>
    )
  }

  return (
    <div className="page notes">
      <div className="notes-head">
        <span className="label">data/notes.md</span>
        <span className="hint">
          {state === 'saving' ? 'saving…' : state === 'failed' ? 'not saved' : 'saved'}
        </span>
      </div>
      <textarea
        className="notes-body"
        value={text}
        spellCheck={false}
        onChange={(event) => change(event.target.value)}
        placeholder="Markdown. Whatever you want to remember about this."
      />
    </div>
  )
}
