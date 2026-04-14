export interface NaceOption {
  code: string
  sectorEn: string
  sectorDe: string
}

export const NACE_OPTIONS: NaceOption[] = [
  { code: 'D35.11', sectorEn: 'Electricity production', sectorDe: 'Elektrizitätserzeugung' },
  { code: 'D35.12', sectorEn: 'Transmission of electricity', sectorDe: 'Elektrizitätsübertragung' },
  { code: 'D35.13', sectorEn: 'Distribution of electricity', sectorDe: 'Elektrizitätsverteilung' },
  { code: 'D35.21', sectorEn: 'Manufacture of gas', sectorDe: 'Gaserzeugung' },
  { code: 'C24.10', sectorEn: 'Basic iron and steel', sectorDe: 'Roheisen und Stahl' },
  { code: 'C23.51', sectorEn: 'Cement', sectorDe: 'Zement' },
  { code: 'C20.14', sectorEn: 'Organic basic chemicals', sectorDe: 'Organische Grundstoffchemie' },
  { code: 'C20.11', sectorEn: 'Industrial gases', sectorDe: 'Industriegase' },
  { code: 'C29.10', sectorEn: 'Motor vehicles', sectorDe: 'Kraftwagen' },
  { code: 'H49.20', sectorEn: 'Freight rail transport', sectorDe: 'Güterbeförderung Eisenbahn' },
  { code: 'H51.10', sectorEn: 'Passenger air transport', sectorDe: 'Personenluftfahrt' },
  { code: 'F41.20', sectorEn: 'Buildings construction', sectorDe: 'Hochbau' },
  { code: 'C16.21', sectorEn: 'Veneer sheets and wood panels', sectorDe: 'Furnier und Holzwerkstoff' },
  { code: 'K64.19', sectorEn: 'Other monetary intermediation', sectorDe: 'Kreditinstitute' },
  { code: 'K65.11', sectorEn: 'Life insurance', sectorDe: 'Lebensversicherung' },
  { code: 'K65.12', sectorEn: 'Non-life insurance', sectorDe: 'Nichtlebensversicherung' },
  { code: 'C10.41', sectorEn: 'Manufacture of oils and fats', sectorDe: 'Herstellung von Ölen und Fetten' },
  { code: 'C19.20', sectorEn: 'Refined petroleum products', sectorDe: 'Mineralölverarbeitung' },
]

export function findNaceOption(code: string | null | undefined): NaceOption | null {
  if (!code) return null
  return NACE_OPTIONS.find((option) => option.code === code) ?? null
}
