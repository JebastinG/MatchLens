import { ScanSearch } from 'lucide-react'

const links = [
  ['Product', '#product'],
  ['How it works', '#how-it-works'],
  ['Privacy', '#privacy'],
]

export function Navbar() {
  return (
    <header className="nav glass">
      <a className="brand" href="#top" aria-label="MatchLens home">
        <span className="brand-mark"><ScanSearch size={18} aria-hidden /></span>
        MatchLens
      </a>
      <nav aria-label="Primary">
        <ul className="nav-links">
          {links.map(([label, href]) => (
            <li key={href}><a href={href}>{label}</a></li>
          ))}
          <li><a className="btn btn-primary btn-sm" href="#workspace">Get started</a></li>
        </ul>
      </nav>
    </header>
  )
}
