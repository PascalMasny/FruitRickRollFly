import { useEffect, useMemo, useState } from 'react'
import { fetchCorpus, fetchCorrections } from '../lib/api'
import type { Corpus, CorpusTrack, Correction } from '../lib/types'

type Family = 'rendition' | 'upload'
type Filter = 'all' | 'song' | 'other' | 'missed' | 'false-alarm'

/**
 * The corpus, interactively.
 *
 * `docs/TRAINING.md` draws the same data and cannot be poked at. This can: it
 * is the same 5th-to-95th-percentile spread per track, sortable and
 * filterable, so the question "which negatives does it think are the song"
 * takes a click rather than a rebuild.
 */
export default function TrainingData() {
  const [corpus, setCorpus] = useState<Corpus | null>(null)
  const [corrections, setCorrections] = useState<Correction[]>([])
  const [error, setError] = useState<string | null>(null)
  const [family, setFamily] = useState<Family>('rendition')
  const [filter, setFilter] = useState<Filter>('all')

  useEffect(() => {
    fetchCorpus().then(setCorpus).catch((problem) => setError(String(problem.message ?? problem)))
    fetchCorrections()
      .then((body) => setCorrections(body.corrections))
      .catch(() => setCorrections([]))
  }, [])

  const rows = useMemo(() => {
    if (!corpus) return []
    const scored = corpus.tracks.filter((track) => track.spread[family])
    const keep = (track: CorpusTrack) => {
      const verdict = track.verdict[family]
      switch (filter) {
        case 'song':
          return track.positive
        case 'other':
          return !track.positive
        case 'missed':
          return track.positive && verdict?.committed === false
        case 'false-alarm':
          return !track.positive && verdict?.committed === true
        default:
          return true
      }
    }
    return scored
      .filter(keep)
      .sort((a, b) => (b.spread[family]?.median ?? 0) - (a.spread[family]?.median ?? 0))
  }, [corpus, family, filter])

  if (error) {
    return (
      <div className="page">
        <p className="hint">{error}</p>
      </div>
    )
  }
  if (!corpus) {
    return (
      <div className="page">
        <p className="hint">reading the corpus…</p>
      </div>
    )
  }

  const positives = corpus.tracks.filter((t) => t.positive).length
  const scored = corpus.tracks.filter((t) => t.spread[family]).length

  return (
    <div className="page training">
      <div className="training-controls">
        <div className="switch">
          {(['rendition', 'upload'] as Family[]).map((option) => (
            <button
              key={option}
              type="button"
              className={`chip ${family === option ? 'chip-on' : ''}`}
              onClick={() => setFamily(option)}
            >
              unheard {option}
            </button>
          ))}
        </div>
        <div className="switch">
          {(
            [
              ['all', 'everything'],
              ['song', 'the song'],
              ['other', 'not the song'],
              ['missed', 'missed'],
              ['false-alarm', 'false alarms'],
            ] as [Filter, string][]
          ).map(([option, label]) => (
            <button
              key={option}
              type="button"
              className={`chip ${filter === option ? 'chip-on' : ''}`}
              onClick={() => setFilter(option)}
            >
              {label}
            </button>
          ))}
        </div>
        <span className="hint">
          {rows.length} of {scored} scored tracks · {positives} of {corpus.tracks.length} are the
          song
        </span>
      </div>

      <div className="training-scroll">
        <table className="corpus">
          <thead>
            <tr>
              <th>track</th>
              <th>kind</th>
              <th className="numeric">median</th>
              <th className="spread-head">
                out-of-fold confidence, 5th to 95th
                <span className="axis">
                  <i>0</i>
                  <i>0.5</i>
                  <i>1</i>
                </span>
              </th>
              <th className="numeric">commits</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((track) => {
              const spread = track.spread[family]!
              const verdict = track.verdict[family]
              const wrong =
                verdict && track.positive !== verdict.committed ? 'wrong' : ''
              return (
                <tr key={track.id} className={wrong}>
                  <td>
                    <a href={track.watchUrl} target="_blank" rel="noreferrer noopener">
                      {track.title}
                    </a>
                  </td>
                  <td className="muted">{track.kind}</td>
                  <td className="numeric">{spread.median.toFixed(3)}</td>
                  <td>
                    <span className="spread">
                      <i className="spread-mid" />
                      <i
                        className={`spread-bar ${track.positive ? 'song' : 'other'}`}
                        style={{
                          left: `${spread.p05 * 100}%`,
                          width: `${Math.max(1, (spread.p95 - spread.p05) * 100)}%`,
                        }}
                      />
                      <i
                        className={`spread-dot ${track.positive ? 'song' : 'other'}`}
                        style={{ left: `${spread.median * 100}%` }}
                      />
                    </span>
                  </td>
                  <td className="numeric">
                    {verdict?.committed ? `${verdict.latency?.toFixed(1)} s` : '—'}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>

        <h2 className="page-title">Corrections</h2>
        <p className="hint">
          Spans marked by hand on the response strip, appended to{' '}
          <code>data/corrections.jsonl</code>. These are the examples the fly met in the wild and
          got wrong, which makes them the most useful labels in the project.
        </p>
        {corrections.length === 0 ? (
          <p className="hint">Nothing yet.</p>
        ) : (
          <table className="corpus">
            <thead>
              <tr>
                <th>when</th>
                <th>video</th>
                <th>span</th>
                <th>called</th>
                <th>note</th>
              </tr>
            </thead>
            <tbody>
              {corrections
                .slice()
                .reverse()
                .map((row) => (
                  <tr key={row.id}>
                    <td className="muted">{row.at.replace('T', ' ').replace('+00:00', '')}</td>
                    <td>
                      <a href={row.url || `https://youtu.be/${row.video_id}`} target="_blank"
                         rel="noreferrer noopener">
                        {row.title || row.video_id}
                      </a>
                    </td>
                    <td className="numeric">
                      {row.start.toFixed(1)}–{row.end.toFixed(1)} s
                    </td>
                    <td className={row.label === 'rickroll' ? 'song' : 'other'}>{row.label}</td>
                    <td className="muted">{row.note}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
