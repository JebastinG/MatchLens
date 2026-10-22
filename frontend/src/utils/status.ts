import type { EvidenceStatus } from '../types/api'

export const STATUS_META: Record<EvidenceStatus, { label: string; blurb: string }> = {
  supported: { label: 'Supported', blurb: 'Retrieved evidence directly supports this requirement.' },
  needs_better_evidence: { label: 'Needs better evidence', blurb: 'A claim exists, but the detail is thin.' },
  related_skill_found: { label: 'Related skill found', blurb: 'Adjacent or transferable evidence, not equivalent.' },
  no_evidence_found: { label: 'No evidence found', blurb: 'Nothing relevant in the sources examined. This is not proof the skill is absent.' },
  uncertain: { label: 'Uncertain', blurb: 'Ambiguous or not reliable enough for a conclusion.' },
}

export const STATUS_ORDER: EvidenceStatus[] = [
  'supported', 'needs_better_evidence', 'related_skill_found', 'no_evidence_found', 'uncertain',
]

export const STAGES: { key: string; label: string }[] = [
  { key: 'queued', label: 'Queued' },
  { key: 'extracting_resume', label: 'Reading resume' },
  { key: 'extracting_requirements', label: 'Identifying requirements' },
  { key: 'retrieving_github', label: 'Fetching public repositories' },
  { key: 'retrieving_evidence', label: 'Retrieving evidence' },
  { key: 'assessing_requirements', label: 'Assessing requirements' },
  { key: 'generating_advice', label: 'Preparing recommendations' },
  { key: 'finalizing', label: 'Saving results' },
]
