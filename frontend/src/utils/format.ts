export function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / 1024 / 1024).toFixed(1)} MB`
}

export function percent(share: number | null): string {
  return share === null ? '—' : `${Math.round(share * 100)}%`
}

/** Only render evidence links that point at github.com over https. */
export function safeGithubUrl(url: string | null): string | null {
  if (!url) return null
  try {
    const u = new URL(url)
    return u.protocol === 'https:' && u.hostname === 'github.com' ? u.toString() : null
  } catch {
    return null
  }
}

export function isGithubUrl(v: string): boolean {
  try {
    const u = new URL(v.trim())
    return (u.protocol === 'https:' || u.protocol === 'http:') && /^(www\.)?github\.com$/i.test(u.hostname) && u.pathname.split('/').filter(Boolean).length >= 1
  } catch {
    return false
  }
}

export function isHttpUrl(v: string): boolean {
  try {
    const u = new URL(v.trim())
    return u.protocol === 'http:' || u.protocol === 'https:'
  } catch {
    return false
  }
}

/** Split text into [before, match, after] around a verified quote, for highlighting. */
export function splitAround(text: string, quote: string | null): [string, string, string] | null {
  if (!quote) return null
  const i = text.toLowerCase().indexOf(quote.toLowerCase())
  return i < 0 ? null : [text.slice(0, i), text.slice(i, i + quote.length), text.slice(i + quote.length)]
}
