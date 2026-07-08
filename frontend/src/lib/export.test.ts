import { describe, expect, it } from 'vitest'
import { buildCSV, escapeCSVCell } from './export'

describe('escapeCSVCell', () => {
  it('returns empty string for null and undefined', () => {
    expect(escapeCSVCell(null)).toBe('')
    expect(escapeCSVCell(undefined)).toBe('')
  })

  it('passes plain values through unquoted', () => {
    expect(escapeCSVCell('Siemens AG')).toBe('Siemens AG')
    expect(escapeCSVCell(2024)).toBe('2024')
    expect(escapeCSVCell(12.5)).toBe('12.5')
  })

  it('quotes values containing commas', () => {
    expect(escapeCSVCell('Müller, Thomas')).toBe('"Müller, Thomas"')
  })

  it('quotes and doubles embedded quotes', () => {
    expect(escapeCSVCell('the "green" fund')).toBe('"the ""green"" fund"')
  })

  it('quotes values containing newlines', () => {
    expect(escapeCSVCell('line1\nline2')).toBe('"line1\nline2"')
  })

  it('preserves zero and negative numbers', () => {
    expect(escapeCSVCell(0)).toBe('0')
    expect(escapeCSVCell(-42.5)).toBe('-42.5')
  })
})

describe('buildCSV', () => {
  it('joins headers and rows with newlines', () => {
    const csv = buildCSV(
      ['Company', 'Year'],
      [
        { Company: 'Contract Demo AG', Year: 2024 },
        { Company: 'RWE, AG', Year: 2023 },
      ]
    )
    expect(csv).toBe('Company,Year\nContract Demo AG,2024\n"RWE, AG",2023')
  })

  it('escapes header cells too', () => {
    expect(buildCSV(['Scope 1 (tCO₂e)', 'a,b'], [])).toBe('Scope 1 (tCO₂e),"a,b"')
  })

  it('produces only the header line for zero rows', () => {
    expect(buildCSV(['A', 'B'], [])).toBe('A,B')
  })
})
