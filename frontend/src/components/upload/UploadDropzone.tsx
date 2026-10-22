import { FileText, Trash2, UploadCloud } from 'lucide-react'
import { useRef, useState } from 'react'
import { formatBytes } from '../../utils/format'

interface Props { file: File | null; onChange: (f: File | null) => void; error?: string; errorId: string; disabled?: boolean }

export function UploadDropzone({ file, onChange, error, errorId, disabled }: Props) {
  const input = useRef<HTMLInputElement>(null)
  const [over, setOver] = useState(false)
  return (
    <div className="field">
      <label className="label" htmlFor="resume-input">Resume (PDF)</label>
      {file ? (
        <div className="file-chip" role="group" aria-label="Selected resume">
          <FileText size={20} aria-hidden />
          <div className="file-meta"><span className="file-name">{file.name}</span><span className="muted">{formatBytes(file.size)}</span></div>
          <button type="button" className="btn btn-ghost btn-sm" disabled={disabled}
            onClick={() => { onChange(null); if (input.current) input.current.value = '' }}>
            <Trash2 size={16} aria-hidden /> Remove
          </button>
        </div>
      ) : (
        <div className={`dropzone ${over ? 'is-over' : ''} ${error ? 'has-error' : ''}`}
          onDragOver={(e) => { e.preventDefault(); setOver(true) }} onDragLeave={() => setOver(false)}
          onDrop={(e) => { e.preventDefault(); setOver(false); onChange(e.dataTransfer.files[0] ?? null) }}>
          <UploadCloud size={22} aria-hidden />
          <p><strong>Drop your PDF here</strong> or choose a file</p>
          <p className="muted">Text-based PDFs only. Scanned images are not supported.</p>
        </div>
      )}
      <input ref={input} id="resume-input" className={file ? 'visually-hidden' : 'file-input'} type="file"
        accept="application/pdf,.pdf" disabled={disabled} aria-invalid={!!error}
        aria-describedby={error ? errorId : undefined} onChange={(e) => onChange(e.target.files?.[0] ?? null)} />
      {error && <p className="field-error" id={errorId}>{error}</p>}
    </div>
  )
}
