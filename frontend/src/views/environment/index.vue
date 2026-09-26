<template>
  <section class="page" data-module="environment">
    <header class="page-head">
      <div>
        <h2>环境监测管理</h2>
        <p class="page-desc">维护环境记录，围绕记录编号、监测区域、温度值、湿度值做登记、筛选与状态流转。</p>
      </div>
      <div class="page-actions">
        <button class="btn primary" type="button" @click="openCreate">登记环境记录</button>
        <button class="btn" type="button" @click="exportRows">导出环境监测清单</button>
      </div>
    </header>

    <div class="stat-row">
      <article v-for="item in stats" :key="item.label" class="stat-card">
        <span class="stat-label">{{ item.label }}</span>
        <strong class="stat-value">{{ item.value }}</strong>
      </article>
    </div>

    <form class="filter-bar" @submit.prevent="reload">
      <label class="filter-item">
        <span>记录编号</span>
        <input v-model="filters.keyword" placeholder="按记录编号检索" />
      </label>
      <label class="filter-item">
        <span>环境状态</span>
        <select v-model="filters.status">
          <option value="">全部状态</option>
          <option v-for="status in statuses" :key="status" :value="status">{{ status }}</option>
        </select>
      </label>
      <button class="btn" type="submit">查询</button>
      <button class="btn ghost" type="button" @click="resetFilters">重置条件</button>
    </form>

    <table class="data-table">
      <thead>
        <tr>
          <th v-for="column in columns" :key="column">{{ column }}</th>
          <th>可执行动作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="String(row.id)">
          <td v-for="column in columns" :key="column">{{ row[column] ?? '—' }}</td>
          <td class="row-actions">
            <button
              v-for="action in actions"
              :key="action"
              class="link"
              type="button"
              @click="runAction(action, row)"
            >
              {{ action }}
            </button>
          </td>
        </tr>
        <tr v-if="!rows.length">
          <td :colspan="columns.length + 1" class="empty-state">暂无环境监测数据，可先登记环境记录</td>
        </tr>
      </tbody>
    </table>

    <footer class="page-foot">
      <span>共 {{ total }} 条环境监测记录</span>
      <span v-if="noticeMessage" class="success-text">{{ noticeMessage }}</span>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>

    <div v-if="showCreate" class="modal-mask" @click.self="closeCreate">
      <div class="modal-card">
        <h3 class="modal-title">登记环境记录</h3>
        <form @submit.prevent="submitCreate">
          <label v-for="field in createFields" :key="field" class="form-item">
            <span>{{ field }}<em v-if="isRequired(field)" class="required-mark">*</em></span>
            <input v-model="draft[field]" :placeholder="placeholderOf(field)" />
            <small v-if="fieldError(field)" class="field-error">{{ fieldError(field) }}</small>
          </label>
          <p v-if="createError" class="error-text">{{ createError }}</p>
          <div class="modal-actions">
            <button class="btn" type="button" :disabled="submitting" @click="closeCreate">取消</button>
            <button class="btn primary" type="submit" :disabled="submitting">
              {{ submitting ? '提交中…' : '提交登记' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'

import { request } from '@/api/client'
import {
  ENVIRONMENT_FIELD_RULES,
  validateEnvironmentEntry,
  type EntryValues,
  type FieldIssue,
} from '@/validation/environment'

type Row = Record<string, string | number | null>

interface ActionResultPayload {
  ok: boolean
  message: string
  entry?: Row
  errors?: Array<{ field: string; code: string; message: string }>
}

const ENDPOINT = '/api/environment'
const columns = ["记录编号", "监测区域", "温度值", "湿度值", "压差值", "记录时间", "记录人员", "环境状态"]
const actions = ["登记预警", "确认超标", "标记恢复"]
const statuses = ["正常", "预警", "超标", "已恢复"]
const stats = [{"label": "正常区域", "value": 0}, {"label": "预警区域", "value": 0}, {"label": "超标区域", "value": 0}]

// 登记表单字段与后端共用校验规则保持同一份清单
const createFields = ENVIRONMENT_FIELD_RULES.map((rule) => rule.name)
const requiredFields = new Set(ENVIRONMENT_FIELD_RULES.filter((rule) => rule.required).map((rule) => rule.name))
const placeholders: Record<string, string> = {
  '记录编号': '如 ENVI-0004，不可与已有记录重复',
  '监测区域': '如 洁净区 / 天平室',
  '温度值': '单位 ℃，允许范围 -50~50',
  '湿度值': '单位 %，允许范围 0~100；可不填',
}

const rows = ref<Row[]>([])
const total = ref(0)
const errorMessage = ref('')
const noticeMessage = ref('')
// 筛选条件与接口参数对齐：记录编号 → keyword，环境状态 → status
const filters = reactive<{ keyword: string; status: string }>({ keyword: '', status: '' })

const showCreate = ref(false)
const submitting = ref(false)
const createError = ref('')
const createIssues = ref<FieldIssue[]>([])
const emptyDraft = (): Record<string, string> =>
  Object.fromEntries(createFields.map((field) => [field, '']))
const draft = reactive<Record<string, string>>(emptyDraft())

function isRequired(field: string): boolean {
  return requiredFields.has(field)
}

function placeholderOf(field: string): string {
  return placeholders[field] ?? `请输入${field}`
}

function fieldError(field: string): string {
  return createIssues.value.find((issue) => issue.field === field)?.message ?? ''
}

function resetFilters() {
  filters.keyword = ''
  filters.status = ''
  void reload()
}

function exportRows() {
  window.open(`${ENDPOINT}/export`, '_blank')
}

function openCreate() {
  Object.assign(draft, emptyDraft())
  createError.value = ''
  createIssues.value = []
  showCreate.value = true
}

function closeCreate() {
  showCreate.value = false
}

async function submitCreate() {
  errorMessage.value = ''
  noticeMessage.value = ''
  createError.value = ''
  // 页面先按共用规则校验一遍，提示与接口完全一致；接口侧仍会复核
  const issues = validateEnvironmentEntry(draft, rows.value as EntryValues[])
  createIssues.value = issues
  if (issues.length) {
    return
  }
  submitting.value = true
  try {
    const response = await request(ENDPOINT, {
      method: 'POST',
      body: JSON.stringify({ values: { ...draft } }),
    })
    const result = (await response.json()) as ActionResultPayload
    if (!response.ok || !result.ok) {
      // 以接口结论为准回填字段级错误，保证两个入口说法一致
      createIssues.value = (result.errors ?? []).map((item) => ({ ...item, code: item.code as FieldIssue['code'] }))
      createError.value = result.message || '环境记录登记失败'
      return
    }
    showCreate.value = false
    noticeMessage.value = result.message || '环境记录已登记'
    await reload()
  } catch (error) {
    createError.value = error instanceof Error ? error.message : '环境记录登记失败'
  } finally {
    submitting.value = false
  }
}

async function runAction(action: string, row: Row) {
  errorMessage.value = ''
  noticeMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/${row.id}/actions`, {
      method: 'POST',
      body: JSON.stringify({ values: { action } }),
    })
    const result = (await response.json()) as ActionResultPayload
    if (!response.ok || !result.ok) {
      throw new Error(result.message || '环境监测动作未生效，请稍后重试')
    }
    noticeMessage.value = result.message
    await reload()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '环境监测操作失败'
  }
}

async function reload() {
  errorMessage.value = ''
  const query = new URLSearchParams()
  if (filters.keyword.trim()) {
    query.set('keyword', filters.keyword.trim())
  }
  if (filters.status) {
    query.set('status', filters.status)
  }
  const suffix = query.toString()
  try {
    const response = await request(suffix ? `${ENDPOINT}?${suffix}` : ENDPOINT)
    if (!response.ok) {
      throw new Error('环境记录列表读取失败')
    }
    const payload = await response.json()
    rows.value = payload.items ?? []
    total.value = payload.total ?? rows.value.length
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '环境监测列表读取失败'
  }
}

onMounted(reload)
</script>
