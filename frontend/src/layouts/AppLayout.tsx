import type { ReactNode } from 'react'
import { Footer } from '../components/layout/Footer'
import { Navbar } from '../components/layout/Navbar'

export function AppLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <a className="skip-link" href="#workspace">Skip to the analyzer</a>
      <Navbar />
      <main>{children}</main>
      <Footer />
    </>
  )
}
