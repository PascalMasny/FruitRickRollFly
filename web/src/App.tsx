import { useCallback, useEffect, useState } from 'react'
import BrainView from './components/BrainView'
import StageStrip from './components/StageStrip'
import Stats from './components/Stats'
import Timeline from './components/Timeline'
import UrlInput from './components/UrlInput'
import VideoPreview from './components/VideoPreview'
import { fetchBrain } from './lib/api'
import type { BrainCard } from './lib/types'
import { useAnalysis } from './lib/useAnalysis'
import { useFrameAt, useReplay } from './lib/usePlayhead'

export default function App() {
  const [card, setCard] = useState<BrainCard | null>(null)
  const [cardError, setCardError] = useState<string | null>(null)
  const analysis = useAnalysis()
  const [videoTime, setVideoTime] = useState(0)
  const [seekTo, setSeekTo] = useState<number | null>(null)

  const duration = analysis.frames.length
    ? (analysis.frames[analysis.frames.length - 1]?.t ?? 0)
    : 0
  const replay = useReplay(duration)

  // Whichever clock moved last is the one the fly follows.
  const at = replay.running ? replay.seconds : videoTime
  const frame = useFrameAt(analysis.frames, at)

  useEffect(() => {
    fetchBrain()
      .then(setCard)
      .catch((error) => setCardError(String(error.message ?? error)))
  }, [])

  useEffect(() => {
    if (analysis.stage === 'queued') {
      setVideoTime(0)
      replay.stop()
    }
    // replay is stable enough for this; only the stage transition matters.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [analysis.stage])

  const onTime = useCallback((seconds: number) => {
    setVideoTime(seconds)
  }, [])

  const seek = useCallback(
    (seconds: number) => {
      if (replay.running) replay.seek(seconds)
      else {
        setSeekTo(seconds)
        setVideoTime(seconds)
      }
    },
    [replay],
  )

  const busy = ['queued', 'resolving', 'fetching', 'hearing', 'judging'].includes(analysis.stage)
  const committed = Boolean(analysis.summary?.verdict)

  if (cardError) {
    return (
      <main className="shell">
        <div className="fatal">
          <h1>No fly</h1>
          <p>{cardError}</p>
          <p className="hint">
            Run <code>uv run frrf-fetch</code> then <code>uv run frrf-train</code>, and restart the
            server.
          </p>
        </div>
      </main>
    )
  }

  return (
    <main className="shell">
      <header className="masthead">
        <div>
          <h1>
            Fruit<span className="accent">Rick</span>Roll<span className="accent">Fly</span>
          </h1>
          <p className="tagline">
            A model of the Drosophila mushroom body that has learned exactly one song.
          </p>
        </div>
        {card && (
          <dl className="masthead-meta">
            <div>
              <dt>target</dt>
              <dd>{card.target}</dd>
            </div>
            <div>
              <dt>corpus</dt>
              <dd>
                {card.corpus.tracks} tracks, {card.corpus.percepts?.toLocaleString()} percepts
              </dd>
            </div>
            <div>
              <dt>trained</dt>
              <dd>{card.trained}</dd>
            </div>
          </dl>
        )}
      </header>

      <UrlInput onSubmit={analysis.run} busy={busy} disabled={!card} />
      <StageStrip stage={analysis.stage} error={analysis.error} />

      {card && (
        <section className="main-grid">
          <div className="panel panel-brain">
            <BrainView circuit={card.circuit} frame={frame} live={Boolean(frame)} />
          </div>
          <aside className="panel panel-stats">
            <Stats card={card} frame={frame} summary={analysis.summary} committed={committed} />
          </aside>
        </section>
      )}

      {analysis.video && (
        <section className="lower-grid">
          <div className="panel panel-video">
            <VideoPreview video={analysis.video} onTime={onTime} seekTo={seekTo} />
            <div className="video-controls">
              <button
                type="button"
                className="chip"
                onClick={() => (replay.running ? replay.stop() : replay.start(0))}
                disabled={!analysis.frames.length}
              >
                {replay.running ? 'stop replay' : 'replay the fly without the video'}
              </button>
              {analysis.summary?.committedAt != null && (
                <button
                  type="button"
                  className="chip"
                  onClick={() => seek(Math.max(0, analysis.summary!.committedAt! - 3))}
                >
                  jump to the moment it knew
                </button>
              )}
            </div>
          </div>
          <div className="panel panel-timeline">
            {card && (
              <Timeline
                frames={analysis.frames}
                summary={analysis.summary}
                at={at}
                commitThreshold={card.circuit.commitThreshold}
                onSeek={seek}
              />
            )}
          </div>
        </section>
      )}

      <footer className="colophon">
        {card?.performance.unheardRendition && card.performance.unheardUpload && (
          <p>
            Held out: {(card.performance.unheardUpload.macroAuc * 100).toFixed(1)} percent AUC on an
            unheard upload of the record,{' '}
            {(card.performance.unheardRendition.macroAuc * 100).toFixed(1)} percent on a rendition it
            has never heard anyone play. Both figures are out of fold.
          </p>
        )}
        <p className="hint">
          The fly is 2,000 Kenyon cells of NumPy. It has never seen the video; it only hears.
        </p>
      </footer>
    </main>
  )
}
