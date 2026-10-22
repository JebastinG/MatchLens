import { FileSearch, Lock, Scale, ShieldAlert } from 'lucide-react'

export function Hero() {
  return (
    <section className="hero container" id="top">
      <div className="hero-copy">
        <p className="eyebrow">Resume-to-job match analyzer</p>
        <h1>Make your next application count.</h1>
        <p className="lede">
          Understand how your resume supports each job requirement—with transparent evidence, honest gaps and
          actionable next steps.
        </p>
        <div className="hero-actions">
          <a className="btn btn-primary" href="#workspace">Analyze my resume</a>
          <a className="btn btn-ghost" href="#how-it-works">How it works</a>
        </div>
      </div>
      <aside className="hero-card glass" id="product" aria-label="What you get">
        <h2 className="h-sm">What you get</h2>
        <ul className="ticks">
          <li><strong>Traceability.</strong> Every finding links to an exact resume quotation or repository path.</li>
          <li><strong>Honest gaps.</strong> “No evidence found” never means “you lack the skill”.</li>
          <li><strong>Truthful advice.</strong> Suggestions clarify what you have; they never invent experience.</li>
        </ul>
      </aside>
    </section>
  )
}

export function HowItWorks() {
  const steps = [
    ['Upload and describe', 'Add your resume PDF and the job as text, a URL or manual requirements. A public GitHub link is optional.'],
    ['Extract requirements', 'The job text is split into individual, checkable requirements.'],
    ['Retrieve evidence', 'Resume passages (and permitted public repository files) are matched to each requirement using retrieval plus explicit rules.'],
    ['Validate and explain', 'A local model may explain findings, but every quotation and reference is verified against the source before it is shown.'],
  ]
  return (
    <section className="container section" id="how-it-works" aria-labelledby="how-h">
      <h2 id="how-h">How it works</h2>
      <ol className="steps">
        {steps.map(([t, d], i) => (
          <li key={t}><span className="step-n" aria-hidden>{i + 1}</span><div><h3 className="h-sm">{t}</h3><p>{d}</p></div></li>
        ))}
      </ol>
    </section>
  )
}

export function PrivacySection() {
  const items = [
    [Lock, 'Local inference', 'Resume content is analyzed by software running on your machine (Ollama). It is not sent to an external AI provider.'],
    [FileSearch, 'Minimal retention', 'The uploaded PDF is deleted as soon as processing ends. Extracted passages and results stay in your local database until you delete the analysis.'],
    [Scale, 'Not a score', 'Coverage figures describe evidence found. They are not an ATS score and do not predict interviews or hiring.'],
    [ShieldAlert, 'Known limits', 'Scanned PDFs are not read (no OCR). Public repository code does not prove authorship or skill. Job-URL and GitHub features contact those sites over the network.'],
  ] as const
  return (
    <section className="container section" id="privacy" aria-labelledby="priv-h">
      <h2 id="priv-h">Privacy-first design and limitations</h2>
      <div className="grid-2">
        {items.map(([Icon, t, d]) => (
          <article key={t} className="card">
            <Icon size={20} aria-hidden className="card-icon" />
            <h3 className="h-sm">{t}</h3>
            <p>{d}</p>
          </article>
        ))}
      </div>
    </section>
  )
}
