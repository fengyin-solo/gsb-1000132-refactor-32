/**
 * 环境记录登记的共用校验口径：缺失、超限、重复、异常值只在这里定义一次。
 * 与后端 backend/app/validation.py 保持同一份规则与同一句文案，
 * 页面提交前先按它给结论，接口返回的说明与之完全一致。
 */

export interface NumberFieldRule {
  min: number
  max: number
  unit: string
}

/** 文本字段：均为必填；记录编号额外要求不可重复。 */
export const TEXT_FIELDS = ['记录编号', '监测区域']

/** 数值字段：均为必填；超出量程即超限，无法解析即异常值。 */
export const NUMBER_FIELD_RULES: Record<string, NumberFieldRule> = {
  温度值: { min: 10, max: 30, unit: '℃' },
  湿度值: { min: 30, max: 80, unit: '%' },
}

export const REQUIRED_FIELDS = [...TEXT_FIELDS, ...Object.keys(NUMBER_FIELD_RULES)]
export const UNIQUE_FIELDS = ['记录编号']

export type EntryValues = Record<string, string | number | null | undefined>

export interface EnvironmentValidation {
  cleaned: Record<string, string | number>
  problems: string[]
}

function isBlank(value: unknown): boolean {
  return value === null || value === undefined || !String(value).trim()
}

function parseNumber(value: unknown): number | null {
  if (typeof value === 'boolean') return null
  if (typeof value === 'number') return Number.isFinite(value) ? value : null
  const text = String(value ?? '').trim()
  if (!text) return null
  const number = Number(text)
  return Number.isFinite(number) ? number : null
}

function fmt(number: number): string {
  return String(number)
}

/** 按统一口径校验一条环境记录；problems 可直接展示，与接口说明逐字一致。 */
export function validateEnvironmentEntry(
  values: EntryValues,
  existingCodes: string[] = [],
): EnvironmentValidation {
  const problems: string[] = []
  const cleaned: Record<string, string | number> = {}

  const missing = REQUIRED_FIELDS.filter((field) => isBlank(values[field]))
  if (missing.length) {
    problems.push(`缺少必填字段：${missing.join('、')}`)
  }

  for (const field of TEXT_FIELDS) {
    const raw = values[field]
    if (isBlank(raw)) continue
    cleaned[field] = String(raw).trim()
  }

  for (const [field, rule] of Object.entries(NUMBER_FIELD_RULES)) {
    const raw = values[field]
    if (isBlank(raw)) continue
    const number = parseNumber(raw)
    if (number === null) {
      problems.push(`${field}异常：「${String(raw).trim()}」不是有效数值`)
      continue
    }
    if (number < rule.min || number > rule.max) {
      problems.push(
        `${field}超限：需在 ${fmt(rule.min)}~${fmt(rule.max)}${rule.unit} 之间，当前 ${fmt(number)}${rule.unit}`,
      )
      continue
    }
    cleaned[field] = number
  }

  for (const field of UNIQUE_FIELDS) {
    const code = cleaned[field]
    if (typeof code === 'string' && code && existingCodes.includes(code)) {
      problems.push(`${field}重复：「${code}」已登记过，请更换`)
    }
  }

  return { cleaned, problems }
}
