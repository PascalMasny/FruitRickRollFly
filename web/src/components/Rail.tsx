import type { BrainCard } from '../lib/types'

interface Props {
  card: BrainCard
  hits: number
  committed: boolean
  busy: boolean
}

/**
 * The left-hand profile column, which is the part of a MySpace page that was
 * never about the content. Everything in it is nonetheless true: the mood is
 * the current verdict, the friend list is the corpus, and the counter counts.
 */
export default function Rail({ card, hits, committed, busy }: Props) {
  const digits = String(hits).padStart(6, '0').split('')
  const rendition = card.performance.unheardRendition
  const mood = busy ? 'listening \u266B' : committed ? 'ROLLED \u2605' : 'unbothered'

  return (
    <div className="rail">
      <section className="card">
        <div className="card-head">
          <span>fruitrickrollfly</span>
        </div>
        <div className="card-body">
          <div className="mugshot" role="img" aria-label="A fruit fly, drawn badly">
            {'\u{1FAB0}'}
          </div>
          <p className="rail-lines" style={{ marginTop: 6 }}>
            <b>Drosophila melanogaster</b>
            <br />
            {card.circuit.kenyonCells.toLocaleString()} Kenyon cells
            <br />
            156 kB &middot; Female
            <br />
            <span className="mood">Mood: {mood}</span>
            <br />
            Last login: {card.trained ?? 'unknown'}
          </p>
          <div className="counter" title="Visits from this browser">
            {digits.map((digit, i) => (
              <span key={i}>{digit}</span>
            ))}
          </div>
        </div>
      </section>

      <section className="card">
        <div className="card-head">
          <span>my friend space</span>
        </div>
        <div className="card-body">
          <p className="rail-lines">
            i have <b>{card.corpus.tracks ?? 0}</b> friends in my corpus.
            <br />
            <b>1</b> of them is my best friend.
          </p>
          <p className="rail-lines" style={{ marginTop: 6 }}>
            <b>Top 1:</b>
            <br />
            {card.target}
          </p>
        </div>
      </section>

      <section className="card">
        <div className="card-head">
          <span>honest disclaimer</span>
        </div>
        <div className="card-body">
          <p className="rail-lines">
            the big number is for another upload of the same 1987 master, which
            is leakage on purpose.
            {rendition && (
              <>
                {' '}
                on a cover nobody has played me i get{' '}
                <b>{(rendition.macroAuc * 100).toFixed(1)}%</b> and thats the
                honest one.
              </>
            )}
          </p>
          <div className="badges" style={{ marginTop: 6 }}>
            <span className="badge">BEST VIEWED IN NETSCAPE</span>
            <span className="badge b2">MADE ON A MAC</span>
            <span className="badge b3">NO FRAMES!</span>
          </div>
        </div>
      </section>
    </div>
  )
}
