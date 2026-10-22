import type { Accepted, AnalysisStatus, FieldError, Results } from '../../types/api'

export const API_BASE: string =
  (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, '') ?? 'http://127.0.0.1:8000/api/v1'

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public fields: FieldError[] = [],
    public details: Record<string, unknown> | null = null,
  ) {
    super(message)
  }
}

type ErrBody = { error?: { code: string; message: string; details?: ({ fields?: FieldError[] } & Record<string, unknown>) | null } }

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(`${API_BASE}${path}`, init)
  } catch {
    throw new ApiError(0, 'network_error', 'Cannot reach the MatchLens backend. Is it running on the configured address?')
  }
  if (res.status === 204) return undefined as T
  let body: unknown = null
  try {
    body = await res.json()
  } catch {
    /* non-JSON body */
  }
  if (!res.ok) {
    const e = (body as ErrBody | null)?.error
    throw new ApiError(res.status, e?.code ?? 'http_error', e?.message ?? `Request failed (${res.status}).`, e?.details?.fields ?? [], e?.details ?? null)
  }
  return body as T
}

export const api = {
  createAnalysis: (form: FormData) => request<Accepted>('/analyses', { method: 'POST', body: form }),
  getStatus: (id: string) => request<AnalysisStatus>(`/analyses/${id}`),
  getResults: (id: string) => request<Results>(`/analyses/${id}/results`),
  dismiss: (id: string, assessmentId: string, dismissed: boolean) =>
    request<{ id: string; dismissed: boolean }>(`/analyses/${id}/assessments/${assessmentId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ dismissed }),
    }),
  remove: (id: string) => request<void>(`/analyses/${id}`, { method: 'DELETE' }),
}
