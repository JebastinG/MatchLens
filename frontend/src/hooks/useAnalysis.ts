import { useCallback, useEffect, useRef, useState } from 'react'
import { api, ApiError } from '../services/api/client'
import type { AnalysisStatus, Results } from '../types/api'

export type Phase = 'idle' | 'submitting' | 'polling' | 'done' | 'failed'
const KEY = 'matchlens.analysisId' // sessionStorage: cleared when the tab closes
const POLL_MS = 1500

export function useAnalysis() {
  const [phase, setPhase] = useState<Phase>('idle')
  const [id, setId] = useState<string | null>(null)
  const [status, setStatus] = useState<AnalysisStatus | null>(null)
  const [results, setResults] = useState<Results | null>(null)
  const [error, setError] = useState<string | null>(null)
  const alive = useRef(true)

  useEffect(() => {
    alive.current = true
    const saved = sessionStorage.getItem(KEY)
    if (saved) {
      setId(saved)
      setPhase('polling')
    }
    return () => { alive.current = false }
  }, [])

  const reset = useCallback(() => {
    sessionStorage.removeItem(KEY)
    setId(null); setStatus(null); setResults(null); setError(null); setPhase('idle')
  }, [])

  useEffect(() => {
    if (phase !== 'polling' || !id) return
    let cancelled = false
    let failures = 0
    let timer: number | undefined
    const tick = async () => {
      try {
        const s = await api.getStatus(id)
        if (cancelled) return
        failures = 0
        setStatus(s)
        if (s.status === 'completed') {
          setResults(await api.getResults(id))
          if (!cancelled) setPhase('done')
          return
        }
        if (s.status === 'failed') {
          setError(s.error_message ?? 'The analysis failed.')
          setPhase('failed')
          return
        }
      } catch (e) {
        if (cancelled) return
        if (e instanceof ApiError && e.status === 404) {
          reset()
          return
        }
        if (++failures >= 4) {
          setError(e instanceof ApiError ? e.message : 'Lost connection to the backend.')
          setPhase('failed')
          return
        }
      }
      timer = window.setTimeout(tick, POLL_MS)
    }
    void tick()
    return () => { cancelled = true; window.clearTimeout(timer) }
  }, [phase, id, reset])

  const submit = useCallback(async (form: FormData) => {
    setPhase('submitting'); setError(null)
    try {
      const acc = await api.createAnalysis(form)
      sessionStorage.setItem(KEY, acc.id)
      setId(acc.id); setStatus(null); setResults(null); setPhase('polling')
      return null
    } catch (e) {
      setPhase('idle')
      return e instanceof ApiError ? e : new ApiError(0, 'unknown', 'Something went wrong.')
    }
  }, [])

  const dismiss = useCallback(async (assessmentId: string, dismissed: boolean) => {
    if (!id) return
    await api.dismiss(id, assessmentId, dismissed)
    setResults(await api.getResults(id))
  }, [id])

  const remove = useCallback(async () => {
    if (id) await api.remove(id)
    reset()
  }, [id, reset])

  return { phase, id, status, results, error, submit, dismiss, remove, reset }
}
