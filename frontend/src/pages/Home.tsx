import { ResultsDashboard } from '../components/analysis/ResultsDashboard'
import { FailurePanel, ProgressPanel } from '../components/analysis/ProgressPanel'
import { HowItWorks, Hero, PrivacySection } from '../components/Sections'
import { Toasts } from '../components/Toasts'
import { AnalysisForm } from '../components/upload/AnalysisForm'
import { useAnalysis } from '../hooks/useAnalysis'
import { useToasts } from '../hooks/useToasts'
import { AppLayout } from '../layouts/AppLayout'
import { ApiError } from '../services/api/client'

export function Home() {
  const an = useAnalysis()
  const { toasts, push, dismiss } = useToasts()
  const formVisible = an.phase === 'idle' || an.phase === 'submitting'

  const guard = (fn: () => Promise<void>, okMsg?: string) => async () => {
    try { await fn(); if (okMsg) push('success', okMsg) } catch (e) { push('error', e instanceof ApiError ? e.message : 'Something went wrong.') }
  }

  return (
    <AppLayout>
      <Hero />
      <section className="container workspace" id="workspace" aria-label="Analyzer">
        {/* Kept mounted (hidden) so inputs survive a failed run and "Back to the form" works as retry. */}
        <div hidden={!formVisible}>
          <AnalysisForm busy={an.phase === 'submitting'} onSubmit={async (fd) => {
            const err = await an.submit(fd)
            if (err?.code === 'network_error' || err?.status === 503) push('error', err.message)
            return err
          }} />
        </div>
        {an.phase === 'polling' && <ProgressPanel status={an.status} />}
        {an.phase === 'failed' && <FailurePanel message={an.error ?? 'The analysis failed.'} onRetry={an.reset} />}
        {an.phase === 'done' && an.results && (
          <ResultsDashboard results={an.results} onNew={an.reset}
            onDismiss={async (id, v) => { try { await an.dismiss(id, v) } catch (e) { push('error', e instanceof ApiError ? e.message : 'Could not update the finding.') } }}
            onDelete={guard(an.remove, 'Analysis deleted.')} />
        )}
      </section>
      <HowItWorks />
      <PrivacySection />
      <Toasts toasts={toasts} onDismiss={dismiss} />
    </AppLayout>
  )
}
