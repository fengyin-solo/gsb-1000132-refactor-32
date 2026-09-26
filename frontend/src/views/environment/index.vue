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

    <form v-if="showCreate" class="filter-bar" @submit.prevent="submitCreate">
      <label v-for="field in createFields" :key="field" class="filter-item">
        <span>{{ field }}</span>
        <input v-model="createForm[field]" :placeholder="createPlaceholder(field)" />
      </label>
      <button class="btn primary" type="submit">提交登记</button>
      <button class="btn ghost" type="button" @click="cancelCreate">取消</button>
    </form>

    <form class="filter-bar" @submit.prevent="reload">
      <label v-for="field in filterFields" :key="field" class="filter-item">
        <span>{{ field }}</span>
        <input v-model="filters[field]" :placeholder="`按${field}检索`" />
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
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { request } from '@/api/client'
import { NUMBER_FIELD_RULES, REQUIRED_FIELDS, validateEnvironmentEntry } from '@/utils/entryValidation'

type Row = Record<string, string | number | null>

const ENDPOINT = '/api/environment'
const columns = ["记录编号", "监测区域", "温度值", "湿度值", "压差值", "记录时间", "记录人员", "环境状态"]
const actions = ["登记预警", "确认超标", "标记恢复"]
const statuses = ["正常", "预警", "超标", "已恢复"]
const stats = [{"label": "正常区域", "value": 0}, {"label": "预警区域", "value": 0}, {"label": "超标区域", "value": 0}]

const rows = ref<Row[]>([])
const total = ref(0)
const errorMessage = ref('')
const filters = ref<Record<string, string>>({})
const filterFields = columns.slice(0, 3)
const showCreate = ref(false)
const createForm = ref<Record<string, string>>({})
const createFields = REQUIRED_FIELDS

function resetFilters() {
  filters.value = {}
  void reload()
}

function exportRows() {
  window.open(`${ENDPOINT}/export`, '_blank')
}

function createPlaceholder(field: string) {
  const rule = NUMBER_FIELD_RULES[field]
  return rule ? `请输入${field}（${rule.min}~${rule.max}${rule.unit}）` : `请输入${field}`
}

function openCreate() {
  errorMessage.value = ''
  createForm.value = {}
  showCreate.value = true
}

function cancelCreate() {
  showCreate.value = false
  createForm.value = {}
}

async function submitCreate() {
  errorMessage.value = ''
  const existingCodes = rows.value.map((row) => String(row['记录编号'] ?? '').trim())
  const { cleaned, problems } = validateEnvironmentEntry(createForm.value, existingCodes)
  if (problems.length) {
    errorMessage.value = problems.join('；')
    return
  }
  try {
    const response = await request(ENDPOINT, {
      method: 'POST',
      body: JSON.stringify({ values: cleaned }),
    })
    const payload = await response.json()
    if (!response.ok || !payload.ok) {
      throw new Error(payload?.message ?? '环境记录登记失败，请稍后重试')
    }
    cancelCreate()
    await reload()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '环境记录登记失败'
  }
}

async function runAction(action: string, row: Row) {
  errorMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/${row.id}/actions`, {
      method: 'POST',
      body: JSON.stringify({ values: { action } }),
    })
    const payload = await response.json()
    if (!response.ok || !payload.ok) {
      throw new Error(payload?.message ?? '环境监测动作未生效，请稍后重试')
    }
    await reload()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '环境监测操作失败'
  }
}

async function reload() {
  errorMessage.value = ''
  const query = new URLSearchParams(filters.value as Record<string, string>).toString()
  try {
    const response = await request(`${ENDPOINT}?${query}`)
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
