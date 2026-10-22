export type EvidenceStatus =
  | 'supported'
  | 'needs_better_evidence'
  | 'related_skill_found'
  | 'no_evidence_found'
  | 'uncertain'

export type AnalysisState = 'queued' | 'processing' | 'completed' | 'failed'
export type JobMode = 'paste' | 'url' | 'manual'

export interface Accepted { id: string; status: AnalysisState; created_at: string; status_url: string; results_url: string }

export interface AnalysisStatus {
  id: string
  status: AnalysisState
  stage: string
  progress: number
  created_at: string
  updated_at: string
  completed_at: string | null
  error_code: string | null
  error_message: string | null
  warnings: string[]
  analysis_mode: 'llm' | 'deterministic' | null
  llm_model: string | null
  embedding_backend: string | null
  resume_filename: string | null
  resume_page_count: number | null
  github_url: string | null
}

export interface Evidence {
  id: string
  ref: string
  source_type: 'resume' | 'github'
  text: string
  quote: string | null
  page_number: number | null
  repo: string | null
  source_url: string | null
  path: string | null
  line_start: number | null
  line_end: number | null
  commit_sha: string | null
  retrieved_at: string | null
}

export interface Assessment {
  id: string
  status: EvidenceStatus
  explanation: string
  method: string
  confidence: null
  warnings: string[]
  dismissed: boolean
  evidence: Evidence[]
}

export interface Requirement { id: string; ordinal: number; text: string; category: string; key_terms: string[]; assessment: Assessment }
export interface Recommendation { id: string; requirement_id: string | null; kind: string; text: string }
export interface InterviewQuestion { id: string; requirement_id: string; question: string; rationale: string; source: string }

export interface Summary {
  total_requirements: number
  dismissed: number
  counts: Record<EvidenceStatus, number>
  direct_support_share: number | null
  evidence_coverage_share: number | null
  definitions: Record<string, string>
  disclaimer: string
}

export interface Results {
  analysis: AnalysisStatus
  job: { mode: string; title: string | null; company: string | null; source_url: string | null }
  summary: Summary
  requirements: Requirement[]
  recommendations: Recommendation[]
  interview_questions: InterviewQuestion[]
}

export interface FieldError { field: string; message: string }
