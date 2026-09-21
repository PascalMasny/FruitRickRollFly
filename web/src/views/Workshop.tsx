import { useCallback, useEffect, useRef, useState } from 'react'
import { chooseModel, fetchJobs, fetchModels, fetchRun, startJob, stopRun } from '../lib/api'
import type { JobState, ModelInfo, ModelState, Run } from '../lib/types'

const SENSES: ('ear' | 'eye')[] = ['ear', 'eye']

function score(model: ModelInfo, family: 'rendition' | 'upload'): string {
  const value = model.scores?.[family]?.macroAuc
  return value == null ? '—' : value.toFixed(3)
}

/**
 * Choosing a fly and running the training commands.
 *
 * A local tool, and it says so: it starts processes on the machine the server
 * is on. The job names are a fixed set and their arguments are built from
 * templates on the server, so nothing typed here reaches a shell.
 */
export default function Workshop() {
  const [models, setModels] = useState<ModelState | null>(null)
  const [jobs, setJobs] = useState<JobState | null>(null)
  const [run, setRun] = useState<Run | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [epochs, setEpochs] = useState(60)
  const [seed, setSeed] = useState(7)
  const [withCorrections, setWithCorrections] = useState(false)
  const log = useRef<HTMLPreElement>(null)

  // Promise chain rather than an awaited call in the effect body, matching
  // the other views: it is the same fetch-on-mount, and the linter can see
  // that nothing here sets state synchronously.
  const refresh = useCallback(
    () =>
      Promise.all([fetchModels(), fetchJobs()])
        .then(([nextModels, nextJobs]) => {
          setModels(nextModels)
          setJobs(nextJobs)
          if (nextJobs.running) setRun(nextJobs.running)
        })
        .catch((problem) => setError(String(problem?.message ?? problem))),
    [],
  )

  useEffect(() => {
    refresh()
  }, [refresh])

  // Poll while something is running. A job prints for minutes, and a poll is
  // less machinery than a second event stream for a page nobody leaves open.
  useEffect(() => {
    if (!run || run.status !== 'running') return
    const timer = window.setInterval(async () => {
      try {
        const next = await fetchRun(run.id)
        setRun(next)
        if (next.status !== 'running') refresh()
      } catch {
        /* the run will be picked up again on the next refresh */
      }
    }, 1200)
    return () => window.clearInterval(timer)
  }, [run, refresh])

  useEffect(() => {
    if (log.current) log.current.scrollTop = log.current.scrollHeight
  }, [run?.lines])

  const launch = async (job: string) => {
    setError(null)
    try {
      const started = await startJob(job, { epochs, seed, withCorrections })
      setRun(await fetchRun(started.id))
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : String(problem))
    }
  }

  const pick = async (sense: string, name: string) => {
    setError(null)
    try {
      setModels(await chooseModel(sense, name === 'default' ? null : name))
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : String(problem))
    }
  }

  if (!models || !jobs) {
    return (
      <div className="page">
        <p className="hint">{error ?? 'looking in models/…'}</p>
      </div>
    )
  }

  const busy = run?.status === 'running'

  return (
    <div className="page workshop">
      <div className="workshop-scroll">
        <h2 className="page-title">Which fly is answering</h2>
        {SENSES.map((sense) => {
          const forSense = models.models.filter((m) => m.sense === sense)
          return (
            <div key={sense} className="sense">
              <div className="sense-head">
                <span className="label">{sense === 'ear' ? 'sound' : 'sight'}</span>
                <span className="hint">
                  {models.active[sense] ?? 'nothing trained for this sense yet'}
                </span>
              </div>
              {forSense.length === 0 ? (
                <p className="hint">
                  {sense === 'eye'
                    ? 'No visual fly exists. Training one has never reached the specificity ' +
                      'floor — the eye scores about 0.62 against the ear’s 0.97. You can ' +
                      'train one below and watch it refuse.'
                    : 'No model in models/. Run fetch, then train.'}
                </p>
              ) : (
                <table className="corpus">
                  <thead>
                    <tr>
                      <th>use</th>
                      <th>model</th>
                      <th>trained</th>
                      <th className="numeric">epochs</th>
                      <th className="numeric">rendition AUC</th>
                      <th className="numeric">upload AUC</th>
                      <th className="numeric">size</th>
                    </tr>
                  </thead>
                  <tbody>
                    {forSense.map((model) => (
                      <tr key={model.name}>
                        <td>
                          <input
                            type="radio"
                            name={`active-${sense}`}
                            checked={models.active[sense] === model.name}
                            onChange={() => pick(sense, model.name)}
                          />
                        </td>
                        <td>{model.name}</td>
                        <td className="muted">{model.trained ?? '—'}</td>
                        <td className="numeric">{model.epochs ?? '—'}</td>
                        <td className="numeric">{score(model, 'rendition')}</td>
                        <td className="numeric">{score(model, 'upload')}</td>
                        <td className="numeric muted">
                          {(model.bytes / 1024).toFixed(0)} kB
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )
        })}

        <h2 className="page-title">Run something</h2>
        <p className="hint">
          These start processes on the machine the server is running on. Job names are a fixed
          set and their arguments are built server-side, so nothing here reaches a shell.
        </p>

        <div className="options">
          <label>
            epochs
            <input
              type="number"
              min={1}
              max={500}
              value={epochs}
              onChange={(event) => setEpochs(Number(event.target.value))}
            />
          </label>
          <label>
            seed
            <input
              type="number"
              min={0}
              value={seed}
              onChange={(event) => setSeed(Number(event.target.value))}
            />
          </label>
          <label className="checkbox">
            <input
              type="checkbox"
              checked={withCorrections}
              onChange={(event) => setWithCorrections(event.target.checked)}
            />
            include hand-marked corrections
          </label>
        </div>

        <div className="jobs">
          {jobs.jobs.map((job) => (
            <button
              key={job.name}
              type="button"
              className="job"
              disabled={busy}
              onClick={() => launch(job.name)}
            >
              <b>{job.label}</b>
              <span>{job.describe}</span>
            </button>
          ))}
        </div>
        {error && <p className="correction-error">{error}</p>}

        {run && (
          <>
            <h2 className="page-title">
              {run.label}
              <span className={`run-status run-${run.status}`}>
                {run.status}
                {run.code != null && run.status !== 'running' ? ` (${run.code})` : ''} ·{' '}
                {run.seconds.toFixed(0)}s
              </span>
              {run.status === 'running' && (
                <button type="button" className="chip" onClick={() => stopRun(run.id)}>
                  stop
                </button>
              )}
            </h2>
            <pre className="log" ref={log}>
              {(run.tail ?? []).join('\n') || 'waiting for output…'}
            </pre>
          </>
        )}

        {jobs.history.length > 1 && (
          <>
            <h2 className="page-title">Earlier runs</h2>
            <table className="corpus">
              <tbody>
                {jobs.history.map((entry) => (
                  <tr key={entry.id}>
                    <td>{entry.label}</td>
                    <td className={`muted run-${entry.status}`}>{entry.status}</td>
                    <td className="numeric muted">{entry.seconds.toFixed(0)} s</td>
                    <td className="muted">{entry.command}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}
      </div>
    </div>
  )
}
