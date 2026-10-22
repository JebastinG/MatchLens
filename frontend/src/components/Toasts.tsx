import { CheckCircle2, Info, X, XCircle } from 'lucide-react'
import type { Toast } from '../hooks/useToasts'

export function Toasts({ toasts, onDismiss }: { toasts: Toast[]; onDismiss: (id: number) => void }) {
  return (
    <div className="toasts" role="status" aria-live="polite">
      {toasts.map((t) => (
        <div key={t.id} className={`toast toast-${t.kind}`}>
          {t.kind === 'error' ? <XCircle size={18} aria-hidden /> : t.kind === 'success' ? <CheckCircle2 size={18} aria-hidden /> : <Info size={18} aria-hidden />}
          <span>{t.text}</span>
          <button className="icon-btn" onClick={() => onDismiss(t.id)} aria-label="Dismiss notification"><X size={16} aria-hidden /></button>
        </div>
      ))}
    </div>
  )
}
