/**
 * 环境记录登记的共用校验：与后端 app/services/environment.py 的 FIELD_RULES
 * 及 app/validation.py 的判定顺序、错误措辞保持一一对应。
 *
 * 页面提交前先跑一遍做即时提示，接口侧仍会复核；两个入口对同一份输入结论一致，
 * 唯一性以接口为准（页面只能看到当前已加载的记录）。规则改动时两边一起改。
 */

export type IssueCode = 'missing' | 'not_number' | 'out_of_range' | 'duplicate'

export interface FieldIssue {
  field: string
  code: IssueCode
  message: string
}

interface FieldRule {
  name: string
  required?: boolean
  unique?: boolean
  numeric?: boolean
  min?: number
  max?: number
}

export type EntryValues = Record<string, string | number | null | undefined>

/** 记录编号、监测区域、温度值、湿度值的登记规则（对应后端 FIELD_RULES） */
export const ENVIRONMENT_FIELD_RULES: FieldRule[] = [
  { name: '记录编号', required: true, unique: true },
  { name: '监测区域', required: true },
  { name: '温度值', required: true, numeric: true, min: -50, max: 50 },
  { name: '湿度值', numeric: true, min: 0, max: 100 },
]

// 数值口径与后端一致：只接受常规十进制写法，排除 inf、nan、下划线等解析歧义
const NUMBER_PATTERN = /^[+-]?(\d+(\.\d+)?|\.\d+)$/

// 错误措辞与后端 app/validation.py 的 MESSAGES 完全一致
const messages = {
  missing: (field: string) => `缺少必填字段：${field}`,
  notNumber: (field: string, value: string) => `${field}应为数值，当前内容无法解析：${value}`,
  outOfRange: (field: string, min: number, max: number, value: string) =>
    `${field}超出允许范围（${min}~${max}），当前值：${value}`,
  duplicate: (field: string, value: string) => `${field}「${value}」已存在，请勿重复登记`,
}

/** 把输入统一成去空白文本；null/undefined 视为空，0 不会被误判为空 */
function textOf(value: string | number | null | undefined): string {
  if (value === null || value === undefined) {
    return ''
  }
  return String(value).trim()
}

/**
 * 按固定顺序（缺失 → 异常值 → 超限 → 重复）校验一份登记数据，返回全部问题；
 * 空数组代表通过。existingRows 用于唯一性预判。
 */
export function validateEnvironmentEntry(
  values: EntryValues,
  existingRows: EntryValues[] = [],
): FieldIssue[] {
  const issues: FieldIssue[] = []
  for (const rule of ENVIRONMENT_FIELD_RULES) {
    const text = textOf(values[rule.name])
    if (rule.required && !text) {
      issues.push({ field: rule.name, code: 'missing', message: messages.missing(rule.name) })
      continue
    }
    if (!text) {
      continue // 选填且留空：不再做数值与重复判断
    }
    if (rule.numeric) {
      if (!NUMBER_PATTERN.test(text)) {
        issues.push({ field: rule.name, code: 'not_number', message: messages.notNumber(rule.name, text) })
        continue
      }
      const number = Number(text)
      const outOfRange =
        (rule.min !== undefined && number < rule.min) ||
        (rule.max !== undefined && number > rule.max)
      if (outOfRange) {
        issues.push({
          field: rule.name,
          code: 'out_of_range',
          message: messages.outOfRange(rule.name, rule.min ?? 0, rule.max ?? 0, text),
        })
        continue
      }
    }
    if (rule.unique && existingRows.some((row) => textOf(row[rule.name]) === text)) {
      issues.push({ field: rule.name, code: 'duplicate', message: messages.duplicate(rule.name, text) })
    }
  }
  return issues
}
