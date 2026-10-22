import { useCallback, useRef, useState } from 'react'

export interface Toast { id: number; kind: 'info' | 'error' | 'success'; text: string }

export function useToasts() {
  const [toasts, setToasts] = useState<Toast[]>([])
  const next = useRef(1)
  const dismiss = useCallback((id: number) => setToasts((t) => t.filter((x) => x.id !== id)), [])
  const push = useCallback((kind: Toast['kind'], text: string) => {
    const id = next.current++
    setToasts((t) => [...t, { id, kind, text }])
    window.setTimeout(() => dismiss(id), 6000)
  }, [dismiss])
  return { toasts, push, dismiss }
}
