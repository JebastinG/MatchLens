import { AlertTriangle, CheckCircle2, CircleSlash, HelpCircle, Link2 } from 'lucide-react'
import type { EvidenceStatus } from '../../types/api'
import { STATUS_META } from '../../utils/status'

const ICONS = {
  supported: CheckCircle2,
  needs_better_evidence: AlertTriangle,
  related_skill_found: Link2,
  no_evidence_found: CircleSlash,
  uncertain: HelpCircle,
} as const

export function StatusBadge({ status }: { status: EvidenceStatus }) {
  const Icon = ICONS[status]
  return (
    <span className={`badge badge-${status}`}>
      <Icon size={14} aria-hidden /> {STATUS_META[status].label}
    </span>
  )
}
