import { FileText, Github } from 'lucide-react'
import type { Evidence } from '../../types/api'
import { safeGithubUrl, splitAround } from '../../utils/format'

export function EvidenceCard({ ev }: { ev: Evidence }) {
  if (ev.source_type === 'resume') {
    const parts = splitAround(ev.text, ev.quote)
    return (
      <figure className="evidence">
        <figcaption><FileText size={14} aria-hidden /> Resume{ev.page_number ? `, page ${ev.page_number}` : ''} <span className="muted">· {ev.ref}</span></figcaption>
        <blockquote>
          {parts ? (<>{parts[0]}<mark>{parts[1]}</mark>{parts[2]}</>) : ev.text}
        </blockquote>
      </figure>
    )
  }
  const href = safeGithubUrl(ev.source_url)
  const lines = ev.line_start ? `L${ev.line_start}${ev.line_end && ev.line_end !== ev.line_start ? `–${ev.line_end}` : ''}` : null
  return (
    <figure className="evidence">
      <figcaption>
        <Github size={14} aria-hidden /> {ev.repo} · <code>{ev.path}</code>{lines ? ` · ${lines}` : ''}
      </figcaption>
      <pre><code>{ev.text}</code></pre>
      <p className="muted small">
        {ev.commit_sha && <>Commit <code>{ev.commit_sha.slice(0, 7)}</code> · </>}
        {ev.retrieved_at && <>Retrieved {new Date(ev.retrieved_at).toLocaleString()} · </>}
        {href ? <a href={href} target="_blank" rel="noopener noreferrer">Open on GitHub</a> : 'Source link unavailable'}
      </p>
      <p className="muted small">Public repository content does not prove authorship or proficiency.</p>
    </figure>
  )
}
