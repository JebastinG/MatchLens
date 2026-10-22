import { describe, expect, it } from 'vitest'
import { formatBytes, isGithubUrl, isHttpUrl, percent, safeGithubUrl, splitAround } from './format'

describe('format utils', () => {
  it('formats bytes and percentages', () => {
    expect(formatBytes(512)).toBe('512 B')
    expect(formatBytes(2 * 1024 * 1024)).toBe('2.0 MB')
    expect(percent(0.5)).toBe('50%')
    expect(percent(null)).toBe('—')
  })
  it('only allows https github links for evidence', () => {
    expect(safeGithubUrl('https://github.com/a/b/blob/x/y.py#L1-L2')).not.toBeNull()
    expect(safeGithubUrl('javascript:alert(1)')).toBeNull()
    expect(safeGithubUrl('https://evil.com/github.com')).toBeNull()
    expect(safeGithubUrl(null)).toBeNull()
  })
  it('validates urls', () => {
    expect(isGithubUrl('https://github.com/octocat')).toBe(true)
    expect(isGithubUrl('https://gitlab.com/octocat')).toBe(false)
    expect(isHttpUrl('ftp://x.com')).toBe(false)
  })
  it('splits around quote case-insensitively', () => {
    expect(splitAround('Built a REST API', 'rest api')).toEqual(['Built a ', 'REST API', ''])
    expect(splitAround('abc', 'zzz')).toBeNull()
    expect(splitAround('abc', null)).toBeNull()
  })
})
