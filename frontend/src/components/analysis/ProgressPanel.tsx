import { Check, Loader2, XCircle } from 'lucide-react'
import type { AnalysisStatus } from '../../types/api'
import { STAGES } from '../../utils/status'

export function ProgressPanel({ status }: { status: AnalysisStatus | null }) {
  const stage = status?.stage ?? 'queued'
  const pct = status?.progress ?? 0
  const idx = Math.max(0, STAGES.findIndex((s) => s.key === stage))
  const label = STAGES[idx]?.label ?? 'Working'
  const showGithub = !!status?.github_url
  return (
    <section className="card progress" aria-labelledby="prog-h">
      <h2 id="prog-h" className="h-md">Analyzing your resume</h2>
      <div className="visually-hidden" role="status" aria-live="polite">{label}, {pct} percent complete</div>
      <progress value={pct} max={100} aria-label="Analysis progress" />
      <ol className="stage-list">
        {STAGES.filter((s) => showGithub || s.key !== 'retrieving_github').map((s) => {
          const i = STAGES.findIndex((x) => x.key === s.key)
          const state = i < idx ? 'done' : i === idx ? 'active' : 'todo'
          return (
            <li key={s.key} className={`stage is-${state}`} aria-current={state === 'active' ? 'step' : undefined}>
              {state === 'done' ? <Check size={16} aria-hidden /> : state === 'active' ? <Loader2 size={16} className="spin" aria-hidden /> : <span className="dot" aria-hidden />}
              {s.label}
            </li>
          )
        })}
      </ol>
      <p className="muted">Local models can take a minute or more. You can leave this tab open.</p>
    </section>
  )
}

export function FailurePanel({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <section className="card failure" role="alert">
      <h2 className="h-md"><XCircle size={20} aria-hidden /> The analysis could not finish</h2>
      <p>{message}</p>
      <button className="btn btn-primary" onClick={onRetry}>Back to the form</button>
    </section>
  )
}
