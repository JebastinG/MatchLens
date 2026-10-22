import { Eye, EyeOff, Trash2 } from 'lucide-react'
import { useRef, useState } from 'react'
import type { Requirement, Results } from '../../types/api'
import { percent } from '../../utils/format'
import { STATUS_META, STATUS_ORDER } from '../../utils/status'
import { EvidenceCard } from '../evidence/EvidenceCard'
import { StatusBadge } from './StatusBadge'

function SummaryCards({ r }: { r: Results }) {
  const s = r.summary
  return (
    <section aria-labelledby="sum-h" className="summary">
      <h3 id="sum-h" className="h-md">Evidence summary</h3>
      <div className="stat-grid">
        <div className="stat"><span className="stat-n">{s.total_requirements - s.dismissed}</span><span>requirements assessed{s.dismissed ? ` (${s.dismissed} dismissed)` : ''}</span></div>
        {STATUS_ORDER.map((k) => (
          <div className="stat" key={k}><span className="stat-n">{s.counts[k]}</span><StatusBadge status={k} /></div>
        ))}
      </div>
      <dl className="metrics">
        <div><dt>Direct support</dt><dd>{percent(s.direct_support_share)}</dd><dd className="muted small">{s.definitions.direct_support_share}</dd></div>
        <div><dt>Evidence coverage</dt><dd>{percent(s.evidence_coverage_share)}</dd><dd className="muted small">{s.definitions.evidence_coverage_share}</dd></div>
      </dl>
      <p className="notice">{s.disclaimer}</p>
    </section>
  )
}

function RequirementCard({ req, onDismiss }: { req: Requirement; onDismiss: (id: string, v: boolean) => Promise<void> }) {
  const a = req.assessment
  const [busy, setBusy] = useState(false)
  return (
    <li className={`req ${a.dismissed ? 'is-dismissed' : ''}`} id={`req-${req.id}`}>
      <div className="req-head">
        <div>
          <p className="req-meta">Requirement {req.ordinal}{req.category !== 'unspecified' ? ` · ${req.category}` : ''}</p>
          <h4 className="req-text">{req.text.replace(/<\/?(excerpt|requirement)>/gi, '')}</h4>
        </div>
        <StatusBadge status={a.status} />
      </div>
      <p>{a.explanation}</p>
      {a.warnings.map((w) => <p key={w} className="warn small">{w}</p>)}
      {a.evidence.length > 0 ? (
        <details>
          <summary>{a.evidence.length} source passage{a.evidence.length > 1 ? 's' : ''}</summary>
          {a.evidence.map((e) => <EvidenceCard key={e.id} ev={e} />)}
        </details>
      ) : (
        <p className="muted small">{STATUS_META[a.status].blurb}</p>
      )}
      <div className="req-actions">
        <span className="muted small">Assessed by {a.method === 'deterministic' ? 'rules' : a.method === 'llm' ? 'rules + local model' : 'rules and model (reconciled)'}</span>
        <button className="btn btn-ghost btn-sm" disabled={busy}
          onClick={async () => { setBusy(true); try { await onDismiss(a.id, !a.dismissed) } finally { setBusy(false) } }}>
          {a.dismissed ? <><Eye size={16} aria-hidden /> Restore finding</> : <><EyeOff size={16} aria-hidden /> Dismiss as incorrect</>}
        </button>
      </div>
    </li>
  )
}

export function ResultsDashboard({ results, onDismiss, onDelete, onNew }: {
  results: Results
  onDismiss: (assessmentId: string, dismissed: boolean) => Promise<void>
  onDelete: () => Promise<void>
  onNew: () => void
}) {
  const dialog = useRef<HTMLDialogElement>(null)
  const [deleting, setDeleting] = useState(false)
  const a = results.analysis
  const reqById = new Map(results.requirements.map((r) => [r.id, r]))
  return (
    <section className="results" aria-labelledby="res-h">
      <div className="results-head">
        <div>
          <h2 id="res-h" className="h-lg">{results.job.title ?? 'Analysis results'}{results.job.company ? ` · ${results.job.company}` : ''}</h2>
          <p className="muted">
            {a.resume_filename} · {a.resume_page_count} page{a.resume_page_count === 1 ? '' : 's'} ·{' '}
            {a.analysis_mode === 'llm' ? `rules + local model (${a.llm_model})` : 'rule-based (local model not used)'} · retrieval: {a.embedding_backend}
          </p>
        </div>
        <div className="head-actions">
          <button className="btn btn-ghost" onClick={onNew}>New analysis</button>
          <button className="btn btn-danger" onClick={() => dialog.current?.showModal()}><Trash2 size={16} aria-hidden /> Delete analysis</button>
        </div>
      </div>

      {a.warnings.length > 0 && (
        <div className="notice warn-box" role="note"><strong>Notes and limitations</strong><ul>{a.warnings.map((w) => <li key={w}>{w}</li>)}</ul></div>
      )}

      <SummaryCards r={results} />

      <section aria-labelledby="req-h">
        <h3 id="req-h" className="h-md">Requirement traceability</h3>
        <ul className="req-list">{results.requirements.map((r) => <RequirementCard key={r.id} req={r} onDismiss={onDismiss} />)}</ul>
      </section>

      <div className="grid-2">
        <section aria-labelledby="rec-h" className="card">
          <h3 id="rec-h" className="h-md">Recommendations</h3>
          {results.recommendations.length === 0 ? <p className="muted">No gaps needing action were found.</p> : (
            <ul className="plain">{results.recommendations.map((x) => {
              const rq = x.requirement_id ? reqById.get(x.requirement_id) : undefined
              return <li key={x.id}><p>{x.text}</p>{rq && <a className="small" href={`#req-${rq.id}`}>Requirement {rq.ordinal}</a>}</li>
            })}</ul>
          )}
        </section>
        <section aria-labelledby="q-h" className="card">
          <h3 id="q-h" className="h-md">Interview preparation</h3>
          {results.interview_questions.length === 0 ? <p className="muted">No questions generated.</p> : (
            <ol className="plain">{results.interview_questions.map((q) => {
              const rq = reqById.get(q.requirement_id)
              return (
                <li key={q.id}><p><strong>{q.question}</strong></p><p className="muted small">Why: {q.rationale}</p>
                  {rq && <a className="small" href={`#req-${rq.id}`}>Requirement {rq.ordinal}</a>}</li>
              )
            })}</ol>
          )}
        </section>
      </div>

      <dialog ref={dialog} className="dialog" aria-labelledby="del-h">
        <h3 id="del-h" className="h-md">Delete this analysis?</h3>
        <p>This permanently removes the extracted job text, requirements, evidence excerpts, findings and recommendations from the local database. This cannot be undone.</p>
        <div className="dialog-actions">
          <button className="btn btn-ghost" onClick={() => dialog.current?.close()} disabled={deleting}>Cancel</button>
          <button className="btn btn-danger" disabled={deleting}
            onClick={async () => { setDeleting(true); try { await onDelete() } finally { setDeleting(false); dialog.current?.close() } }}>
            {deleting ? 'Deleting…' : 'Delete permanently'}
          </button>
        </div>
      </dialog>
    </section>
  )
}
