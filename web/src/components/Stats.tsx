import type { BrainCard, Frame, Summary } from '../lib/types'

interface Props {
  card: BrainCard
  frame: Frame | null
  summary: Summary | null
  committed: boolean
}

function percent(value: number | null | undefined): string {
  return value == null ? 'n/a' : `${(value * 100).toFixed(1)} %`
}

function seconds(value: number | null | undefined): string {
  return value == null ? 'never' : `${value.toFixed(1)} s`
}

/** A labelled bar. Everything on this panel is bounded, so everything is a bar. */
function Meter({ label, value, tone }: { label: string; value: number; tone: string }) {
  return (
    <div className="meter">
      <div className="meter-head">
        <span>{label}</span>
        <span className="meter-value">{(value * 100).toFixed(0)}</span>
      </div>
      <div className="meter-track">
        <div
          className="meter-fill"
          style={{ width: `${Math.max(0, Math.min(1, value)) * 100}%`, background: tone }}
        />
      </div>
    </div>
  )
}

export default function Stats({ card, frame, summary, committed }: Props) {
  const confidence = frame?.confidence ?? 0
  const dopamine = frame?.dopamine ?? 0
  const aversion = frame?.aversion ?? 0
  const upload = card.performance.unheardUpload

  return (
    <div className="stats">
      <div className={`verdict verdict-${committed ? 'yes' : summary ? 'no' : 'idle'}`}>
        <span className="verdict-label">
          {committed ? 'Rickroll' : summary ? 'Not a Rickroll' : 'Waiting'}
        </span>
        <span className="verdict-sub">
          {committed
            ? `dopamine crossed threshold at ${seconds(summary?.committedAt)}`
            : summary
              ? 'the pool never reached threshold'
              : 'paste a link'}
        </span>
      </div>

      <Meter label="confidence in this percept" value={confidence} tone="var(--wing)" />
      <Meter label="dopamine pool" value={dopamine} tone="var(--amber)" />
      <Meter label="aversion pool" value={aversion} tone="var(--eye)" />

      <dl className="readout">
        <div>
          <dt>MBON approach</dt>
          <dd>{(frame?.approach ?? 0).toFixed(3)}</dd>
        </div>
        <div>
          <dt>MBON avoidance</dt>
          <dd>{(frame?.avoidance ?? 0).toFixed(3)}</dd>
        </div>
        <div>
          <dt>valence</dt>
          <dd>{(frame?.valence ?? 0).toFixed(4)}</dd>
        </div>
        <div>
          <dt>Kenyon cells firing</dt>
          <dd>
            {frame?.kenyon.length ?? 0} / {card.circuit.kenyonCells}
          </dd>
        </div>
        <div>
          <dt>commit threshold</dt>
          <dd>{card.circuit.commitThreshold.toFixed(2)}</dd>
        </div>
        <div>
          <dt>percept window</dt>
          <dd>{card.circuit.windowSeconds.toFixed(2)} s</dd>
        </div>
      </dl>

      {summary && (
        <>
          <h3 className="panel-title">This video</h3>
          <dl className="readout">
            <div>
              <dt>first suspicion</dt>
              <dd>{seconds(summary.firstSuspicionAt)}</dd>
            </div>
            <div>
              <dt>committed</dt>
              <dd>{seconds(summary.committedAt)}</dd>
            </div>
            <div>
              <dt>peak confidence</dt>
              <dd>{percent(summary.peakConfidence)}</dd>
            </div>
            <div>
              <dt>percepts above half</dt>
              <dd>{percent(summary.fractionAboveHalf)}</dd>
            </div>
            <div>
              <dt>percepts heard</dt>
              <dd>{summary.percepts}</dd>
            </div>
            <div>
              <dt>analysed in</dt>
              <dd>
                {summary.analysisSeconds.toFixed(1)} s
                {summary.realtimeFactor ? ` (${summary.realtimeFactor}x real time)` : ''}
              </dd>
            </div>
          </dl>
        </>
      )}

      {upload && (
        <>
          <h3 className="panel-title">Held out, unheard upload</h3>
          <dl className="readout">
            <div>
              <dt>track recall</dt>
              <dd>{percent(upload.tracks.recall)}</dd>
            </div>
            <div>
              <dt>track specificity</dt>
              <dd>{percent(upload.tracks.specificity)}</dd>
            </div>
            <div>
              <dt>percept AUC</dt>
              <dd>{upload.macroAuc.toFixed(3)}</dd>
            </div>
            <div>
              <dt>median first suspicion</dt>
              <dd>{seconds(upload.medianFirstSuspicion)}</dd>
            </div>
          </dl>
        </>
      )}
    </div>
  )
}
