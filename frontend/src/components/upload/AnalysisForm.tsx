import { Loader2, Lock } from 'lucide-react'
import { useRef, useState } from 'react'
import type { ApiError } from '../../services/api/client'
import type { JobMode } from '../../types/api'
import { isGithubUrl, isHttpUrl } from '../../utils/format'
import { UploadDropzone } from './UploadDropzone'

const MAX_MB = 5 // matches the backend default MAX_UPLOAD_MB; the server is authoritative
const MODES: { id: JobMode; label: string }[] = [
  { id: 'paste', label: 'Paste text' },
  { id: 'url', label: 'Job URL' },
  { id: 'manual', label: 'Manual entry' },
]

type Errors = Record<string, string>

export function AnalysisForm({ busy, onSubmit }: { busy: boolean; onSubmit: (f: FormData) => Promise<ApiError | null> }) {
  const [file, setFile] = useState<File | null>(null)
  const [mode, setMode] = useState<JobMode>('paste')
  const [v, setV] = useState({ job_description: '', job_url: '', manual_title: '', manual_company: '', manual_requirements: '', github_url: '' })
  const [errors, setErrors] = useState<Errors>({})
  const [formError, setFormError] = useState<string | null>(null)
  const tabRefs = useRef<Record<string, HTMLButtonElement | null>>({})
  const set = (k: keyof typeof v) => (e: { target: { value: string } }) => setV((s) => ({ ...s, [k]: e.target.value }))

  function validate(): Errors {
    const e: Errors = {}
    if (!file) e.resume = 'Choose a PDF resume.'
    else if (!/\.pdf$/i.test(file.name) && file.type !== 'application/pdf') e.resume = 'Only PDF files are supported.'
    else if (file.size > MAX_MB * 1024 * 1024) e.resume = `The file is larger than ${MAX_MB} MB.`
    if (mode === 'paste' && v.job_description.trim().length < 50) e.job_description = 'Paste the job description (at least 50 characters).'
    if (mode === 'url' && !isHttpUrl(v.job_url)) e.job_url = 'Enter a valid http(s) job URL.'
    if (mode === 'manual') {
      if (!v.manual_title.trim()) e.manual_title = 'A job title is required.'
      if (!v.manual_requirements.trim()) e.manual_requirements = 'Enter at least one requirement, one per line.'
    }
    if (v.github_url.trim() && !isGithubUrl(v.github_url)) e.github_url = 'Enter a public github.com profile or repository URL.'
    return e
  }

  async function handle(ev: React.FormEvent) {
    ev.preventDefault()
    if (busy) return
    const e = validate()
    setErrors(e); setFormError(null)
    if (Object.keys(e).length) return
    const fd = new FormData()
    fd.append('resume', file as File)
    fd.append('job_mode', mode)
    if (mode === 'paste') fd.append('job_description', v.job_description)
    if (mode === 'url') fd.append('job_url', v.job_url.trim())
    if (mode === 'manual') {
      fd.append('manual_title', v.manual_title)
      fd.append('manual_requirements', v.manual_requirements)
      if (v.manual_company.trim()) fd.append('manual_company', v.manual_company)
    }
    if (v.github_url.trim()) fd.append('github_url', v.github_url.trim())
    const err = await onSubmit(fd)
    if (err) {
      const fe: Errors = {}
      err.fields.forEach((f) => { fe[f.field === 'job_description' || f.field in v ? f.field : 'resume'] = f.message })
      if (!err.fields.length) {
        if (['file_too_large', 'unsupported_file_type', 'pdf_corrupt', 'pdf_encrypted', 'pdf_no_text', 'pdf_empty', 'pdf_too_many_pages'].includes(err.code)) fe.resume = err.message
        else if (err.code === 'job_page_unavailable') fe.job_url = err.message
      }
      setErrors(fe)
      if (!Object.keys(fe).length) setFormError(err.message)
    }
  }

  function onTabKey(e: React.KeyboardEvent, i: number) {
    if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return
    const n = MODES[(i + (e.key === 'ArrowRight' ? 1 : MODES.length - 1)) % MODES.length]
    setMode(n.id)
    tabRefs.current[n.id]?.focus()
  }

  const err = (k: string) => (errors[k] ? { 'aria-invalid': true, 'aria-describedby': `err-${k}` } : {})
  const msg = (k: string) => errors[k] && <p className="field-error" id={`err-${k}`}>{errors[k]}</p>

  return (
    <form className="card form glass-soft" onSubmit={handle} noValidate aria-busy={busy}>
      <UploadDropzone file={file} onChange={setFile} error={errors.resume} errorId="err-resume" disabled={busy} />

      <div className="field">
        <span className="label" id="job-label">Job description</span>
        <div role="tablist" aria-labelledby="job-label" className="tabs">
          {MODES.map((m, i) => (
            <button key={m.id} type="button" role="tab" id={`tab-${m.id}`} aria-selected={mode === m.id} aria-controls={`panel-${m.id}`}
              tabIndex={mode === m.id ? 0 : -1} ref={(el) => { tabRefs.current[m.id] = el }}
              className={`tab ${mode === m.id ? 'is-active' : ''}`} onClick={() => setMode(m.id)} onKeyDown={(e) => onTabKey(e, i)} disabled={busy}>
              {m.label}
            </button>
          ))}
        </div>
        <div role="tabpanel" id={`panel-${mode}`} aria-labelledby={`tab-${mode}`} className="tabpanel">
          {mode === 'paste' && (<>
            <label className="sr-label" htmlFor="job_description">Job description text</label>
            <textarea id="job_description" rows={8} value={v.job_description} onChange={set('job_description')} disabled={busy}
              placeholder="Paste the full job posting, including the requirements section." {...err('job_description')} />
            {msg('job_description')}
          </>)}
          {mode === 'url' && (<>
            <label className="sr-label" htmlFor="job_url">Job posting URL</label>
            <input id="job_url" type="url" inputMode="url" value={v.job_url} onChange={set('job_url')} disabled={busy}
              placeholder="https://company.example/jobs/123" {...err('job_url')} />
            <p className="hint">Public pages only. Pages that need JavaScript or a login can’t be read; paste the text instead.</p>
            {msg('job_url')}
          </>)}
          {mode === 'manual' && (<>
            <div className="row">
              <div className="field">
                <label className="label" htmlFor="manual_title">Job title</label>
                <input id="manual_title" value={v.manual_title} onChange={set('manual_title')} disabled={busy} {...err('manual_title')} />
                {msg('manual_title')}
              </div>
              <div className="field">
                <label className="label" htmlFor="manual_company">Company <span className="muted">(optional)</span></label>
                <input id="manual_company" value={v.manual_company} onChange={set('manual_company')} disabled={busy} />
              </div>
            </div>
            <label className="label" htmlFor="manual_requirements">Requirements (one per line)</label>
            <textarea id="manual_requirements" rows={6} value={v.manual_requirements} onChange={set('manual_requirements')} disabled={busy}
              placeholder={'3+ years of Python\nExperience with PostgreSQL'} {...err('manual_requirements')} />
            {msg('manual_requirements')}
          </>)}
        </div>
      </div>

      <div className="field">
        <label className="label" htmlFor="github_url">Public GitHub profile or repository <span className="muted">(optional)</span></label>
        <input id="github_url" type="url" value={v.github_url} onChange={set('github_url')} disabled={busy}
          placeholder="https://github.com/username/repository" {...err('github_url')} />
        <p className="hint">Only public files are read, and never executed. Public code does not prove authorship or proficiency.</p>
        {msg('github_url')}
      </div>

      <p className="privacy-note"><Lock size={16} aria-hidden /> Analysis runs on your machine. Your PDF is deleted when processing finishes; results stay local until you delete them.</p>

      {formError && <p className="field-error" role="alert">{formError}</p>}
      <button className="btn btn-primary btn-lg" type="submit" disabled={busy}>
        {busy ? (<><Loader2 className="spin" size={18} aria-hidden /> Submitting…</>) : 'Analyze'}
      </button>
    </form>
  )
}
