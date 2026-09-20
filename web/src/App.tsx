import { useCallback, useEffect, useMemo, useState } from 'react'
import BrainView from './components/BrainView'
import Rail from './components/Rail'
import StageStrip from './components/StageStrip'
import Stats from './components/Stats'
import Timeline from './components/Timeline'
import UrlInput from './components/UrlInput'
import VideoPreview from './components/VideoPreview'
import { fetchBrain } from './lib/api'
import type { BrainCard } from './lib/types'
import { useAnalysis } from './lib/useAnalysis'
import { useFrameAt, useReplay } from './lib/usePlayhead'

const TICKER =
  '★ WELCOME 2 MY PROFILE ★ i am a fruit fly and i know ONE song ★ ' +
  'paste a youtube link and watch my dopamine go crazy!!! ★ ' +
  'no haters ★ 200 of my 4000 kenyon cells fire at a time thats just how i am ★ ' +
  'PLZ SIGN MY GUESTBOOK ★'

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

  /* A hit counter, because it is 2003. It counts real visits to this browser
     and nothing else, which makes it the most honest counter of its era. */
  const hits = useMemo(() => {
    try {
      const next = Number(localStorage.getItem('frrf.hits') ?? '0') + 1
      localStorage.setItem('frrf.hits', String(next))
      return next
    } catch {
      return 1
    }
  }, [])

  if (cardError) {
    return (
      <main className="shell" style={{ display: 'grid', placeItems: 'center' }}>
        <div className="fatal">
          <h1>404 NO FLY</h1>
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
        <h1 className="wordart">
          Fruit<span className="accent">Rick</span>Roll<span className="accent">Fly</span>
        </h1>
        <div className="marquee">
          <span>{TICKER}</span>
        </div>
        {card && (
          <dl className="masthead-meta">
            <div>
              <dt>trained</dt>
              <dd>{card.trained}</dd>
            </div>
            <div>
              <dt>corpus</dt>
              <dd>
                {card.corpus.tracks} tracks / {card.corpus.percepts?.toLocaleString()} percepts
              </dd>
            </div>
          </dl>
        )}
      </header>

      {card && <Rail card={card} hits={hits} committed={committed} busy={busy} />}

      <section className="card brain">
        <div className="card-head">
          <span>~*~ my brain ~*~</span>
          <span>mushroom body, live</span>
        </div>
        <div className="card-body flush">
          {card && <BrainView circuit={card.circuit} frame={frame} live={Boolean(frame)} />}
        </div>
      </section>

      <section className="card bar">
        <div className="card-head">
          <span>play me something</span>
          <span className="blink">{busy ? 'LISTENING...' : 'ONLINE NOW!'}</span>
        </div>
        <div className="card-body">
          <UrlInput onSubmit={analysis.run} busy={busy} disabled={!card} />
          <StageStrip stage={analysis.stage} error={analysis.error} />
        </div>
      </section>

      <div className="side">
        <section className="card side-video">
          <div className="card-head">
            <span>now playing</span>
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
          <div className="card-body flush">
            {analysis.video ? (
              <>
                <VideoPreview video={analysis.video} onTime={onTime} seekTo={seekTo} />
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
                <span className="big">♫</span>
                <span>nothing in the CD tray yet</span>
                <span className="hint">paste a link and i will listen</span>
              </div>
            )}
          </div>
        </section>

        <section className="card side-stats">
          <div className="card-head">
            <span>my details</span>
          </div>
          <div className="card-body">
            {card && (
              <Stats card={card} frame={frame} summary={analysis.summary} committed={committed} />
            )}
          </div>
        </section>
      </div>

      <section className="card time">
        <div className="card-head">
          <span>the whole song, second by second</span>
          <span>click to seek</span>
        </div>
        <div className="card-body">
          {card && analysis.frames.length > 0 ? (
            <Timeline
              frames={analysis.frames}
              summary={analysis.summary}
              at={at}
              commitThreshold={card.circuit.commitThreshold}
              onSeek={seek}
            />
          ) : (
            <p className="hint" style={{ fontSize: '0.66rem' }}>
              {card?.performance.unheardUpload && card.performance.unheardRendition
                ? `held out: ${(card.performance.unheardUpload.macroAuc * 100).toFixed(1)}% AUC on an unheard upload of the record, ` +
                  `${(card.performance.unheardRendition.macroAuc * 100).toFixed(1)}% on a rendition it has never heard anyone play. both out of fold.`
                : 'no song yet.'}
            </p>
          )}
        </div>
      </section>
    </main>
  )
}
