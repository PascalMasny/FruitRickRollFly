import { useCallback, useEffect, useState } from 'react'
import BrainView from './components/BrainView'
import Ear from './components/Ear'
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
      <main className="shell" style={{ display: 'grid', placeItems: 'center' }}>
        <div className="fatal">
          <h1>No fly</h1>
          <p>{cardError}</p>
          <p className="hint">
            Run <code>frrf-fetch</code> then <code>frrf-train</code>, and restart the server.
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
            A Drosophila mushroom body that has learned exactly one song.
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

      <section className="panel brain">
        <div className="panel-head">
          <span className="label">mushroom body</span>
          <span className="label">right hemisphere, measured</span>
        </div>
        {card && (
          <>
            <BrainView circuit={card.circuit} frame={frame} live={Boolean(frame)} />
            <div className="ear">
              <Ear circuit={card.circuit} frame={frame} />
              <div className="ear-key">
                <b className="mel">{card.circuit.melBands} tonotopic</b>
                <b className="chroma">{card.circuit.chromaBands} pitch classes</b>
                <b>&times;{card.circuit.subframes} sub-frames</b>
              </div>
            </div>
          </>
        )}
      </section>

      <section className="panel bar">
        <div className="panel-head">
          <span className="label">play it something</span>
          <span className="label">{busy ? 'listening' : 'idle'}</span>
        </div>
        <div>
          <UrlInput onSubmit={analysis.run} busy={busy} disabled={!card} />
          <StageStrip stage={analysis.stage} error={analysis.error} />
        </div>
      </section>

      <div className="side">
        <section className="panel side-video">
          <div className="panel-head">
            <span className="label">now playing</span>
            {analysis.summary?.committedAt != null && (
              <button
                type="button"
                className="chip"
                onClick={() => seek(Math.max(0, analysis.summary!.committedAt! - 3))}
              >
                the moment it knew
              </button>
            )}
          </div>
          {analysis.video ? (
            <>
              <VideoPreview
                video={analysis.video}
                src={analysis.mediaUrl}
                onTime={onTime}
                seekTo={seekTo}
              />
              <div className="video-controls">
                <button
                  type="button"
                  className="chip"
                  onClick={() => (replay.running ? replay.stop() : replay.start(0))}
                  disabled={!analysis.frames.length}
                >
                  {replay.running ? 'stop replay' : 'replay without the video'}
                </button>
              </div>
            </>
          ) : (
            <div className="video-empty">
              <span>nothing playing</span>
              <span>paste a link</span>
            </div>
          )}
        </section>

        <section className="panel side-stats">
          {card && (
            <Stats card={card} frame={frame} summary={analysis.summary} committed={committed} />
          )}
        </section>
      </div>

      <section className="panel time">
        <div className="panel-head">
          <span className="label">the whole response</span>
          <span className="label">click to seek</span>
        </div>
        {card && analysis.frames.length > 0 ? (
          <Timeline
            frames={analysis.frames}
            summary={analysis.summary}
            at={at}
            commitThreshold={card.circuit.commitThreshold}
            onSeek={seek}
          />
        ) : (
          <p className="hint">
            {card?.performance.unheardUpload && card.performance.unheardRendition
              ? `Held out: ${(card.performance.unheardUpload.macroAuc * 100).toFixed(1)}% AUC on an unheard upload of the record, ` +
                `${(card.performance.unheardRendition.macroAuc * 100).toFixed(1)}% on a rendition it has never heard anyone play. Both out of fold.`
              : 'Nothing heard yet.'}
          </p>
        )}
      </section>
    </main>
  )
}
