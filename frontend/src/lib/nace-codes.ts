export interface NaceOption {
  code: string
  sectorEn: string
  sectorDe: string
  sectorZh: string
}

export const NACE_OPTIONS: NaceOption[] = [
  { code: 'D35.11', sectorEn: 'Electricity production', sectorDe: 'Elektrizitätserzeugung', sectorZh: '电力生产' },
  { code: 'D35.12', sectorEn: 'Transmission of electricity', sectorDe: 'Elektrizitätsübertragung', sectorZh: '电力传输' },
  { code: 'D35.13', sectorEn: 'Distribution of electricity', sectorDe: 'Elektrizitätsverteilung', sectorZh: '电力配送' },
  { code: 'D35.21', sectorEn: 'Manufacture of gas', sectorDe: 'Gaserzeugung', sectorZh: '燃气制造' },
  { code: 'C24.10', sectorEn: 'Basic iron and steel', sectorDe: 'Roheisen und Stahl', sectorZh: '生铁与粗钢' },
  { code: 'C23.51', sectorEn: 'Cement', sectorDe: 'Zement', sectorZh: '水泥' },
  { code: 'C20.14', sectorEn: 'Organic basic chemicals', sectorDe: 'Organische Grundstoffchemie', sectorZh: '有机基础化学品' },
  { code: 'C20.11', sectorEn: 'Industrial gases', sectorDe: 'Industriegase', sectorZh: '工业气体' },
  { code: 'C29.10', sectorEn: 'Motor vehicles', sectorDe: 'Kraftwagen', sectorZh: '机动车制造' },
  { code: 'H49.20', sectorEn: 'Freight rail transport', sectorDe: 'Güterbeförderung Eisenbahn', sectorZh: '铁路货运' },
  { code: 'H51.10', sectorEn: 'Passenger air transport', sectorDe: 'Personenluftfahrt', sectorZh: '航空客运' },
  { code: 'F41.20', sectorEn: 'Buildings construction', sectorDe: 'Hochbau', sectorZh: '房屋建筑' },
  { code: 'C16.21', sectorEn: 'Veneer sheets and wood panels', sectorDe: 'Furnier und Holzwerkstoff', sectorZh: '饰面薄板和木板' },
  { code: 'K64.19', sectorEn: 'Other monetary intermediation', sectorDe: 'Kreditinstitute', sectorZh: '其他货币中介服务' },
  { code: 'K65.11', sectorEn: 'Life insurance', sectorDe: 'Lebensversicherung', sectorZh: '人寿保险' },
  { code: 'K65.12', sectorEn: 'Non-life insurance', sectorDe: 'Nichtlebensversicherung', sectorZh: '非人寿保险' },
  { code: 'C10.41', sectorEn: 'Manufacture of oils and fats', sectorDe: 'Herstellung von Ölen und Fetten', sectorZh: '油脂制造' },
  { code: 'C19.20', sectorEn: 'Refined petroleum products', sectorDe: 'Mineralölverarbeitung', sectorZh: '精炼石油产品' },
]

export function findNaceOption(code: string | null | undefined): NaceOption | null {
  if (!code) return null
  return NACE_OPTIONS.find((option) => option.code === code) ?? null
}

export function getLocalizedSector(option: NaceOption | null | undefined, locale: string | null | undefined): string {
  if (!option) return ''
  const lang = (locale || 'en').split('-')[0]
  if (lang === 'zh') return option.sectorZh
  if (lang === 'de') return option.sectorDe
  return option.sectorEn
}
