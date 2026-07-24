/**
 * 分类字段级联逻辑（操作员行内编辑复用）
 *
 * 加载策略（A+D）：
 * - A 懒加载：展开下拉时再请求该字段选项
 * - D 缓存：相同规则版本 + 字段 + 路径 复用结果
 */
import { reactive } from 'vue'
import { getFieldMetaApi, getRuleOptionsApi, getRuleVersionApi } from '@/api/rules'

const CASCADE_ORDER = [
  'category_large',
  'category_segment',
  'category_type',
  'material_main',
  'material_aux',
  'packaging',
  'size',
]

const FIELD_API_MAP = {
  category_large: '大类',
  category_segment: '区隔',
  category_type: '类别',
  material_main: '主材质',
  material_aux: '辅材质',
  packaging: '包装方式',
}

const OPTION_KEY_MAP = {
  category_large: 'large',
  category_segment: 'segment',
  category_type: 'type',
  material_main: 'materialMain',
  material_aux: 'materialAux',
  packaging: 'packaging',
  size: 'size',
  roll_count: 'roll',
  total_count: 'total',
}

/** 尺寸/卷数/总入数：走 field-meta 接口 */
const TAIL_META_MAP = {
  size: { fieldName: '尺寸', targetKey: 'size', optionKey: 'size', rowField: 'size' },
  roll_count: { fieldName: '卷数', targetKey: 'roll', optionKey: 'roll', rowField: 'roll_count' },
  total_count: { fieldName: '总入数', targetKey: 'total', optionKey: 'total', rowField: 'total_count' },
}

const DOWNSTREAM_CLEARS = {
  category_large: ['category_segment', 'category_type', 'material_main', 'material_aux', 'packaging', 'size', 'roll_count', 'total_count'],
  category_segment: ['category_type', 'material_main', 'material_aux', 'packaging', 'size', 'roll_count', 'total_count'],
  category_type: ['material_main', 'material_aux', 'packaging', 'size', 'roll_count', 'total_count'],
  material_main: ['material_aux', 'packaging', 'size', 'roll_count', 'total_count'],
  material_aux: ['packaging', 'size', 'roll_count', 'total_count'],
  packaging: ['size', 'roll_count', 'total_count'],
  size: ['roll_count', 'total_count'],
}

/** 填写时可多选的分类字段（大类为单选，不在此列） */
export const MULTI_SELECT_FIELDS = [
  'category_segment',
  'category_type',
  'material_main',
  'material_aux',
  'packaging',
  'size',
  'roll_count',
  'total_count',
]

/**
 * 大类单选值规范化（兼容历史逗号多选 / 数组，编辑时只保留第一个）
 */
export function normalizeSingleLarge(value) {
  if (Array.isArray(value)) {
    const first = value.map((v) => String(v).trim()).find(Boolean)
    return first || ''
  }
  if (typeof value === 'string' && value.trim()) {
    const parts = value.split(/[,，]/).map((s) => s.trim()).filter(Boolean)
    return parts[0] || ''
  }
  return value ? String(value).trim() : ''
}

/** 全局大类选项（所有行共用；规则版本变化时自动刷新） */
export const globalLargeOptions = reactive({ list: [], versionId: null })

/** 前端已知的最新规则版本 id */
let knownRuleVersionId = null

/**
 * 规则选项/元数据缓存。
 * key = versionId|kind|field|stablePathJson
 */
const pathResultCache = new Map()

/** 进行中的相同请求，避免并发重复打接口 */
const inflightRequests = new Map()

function stablePathJson(path) {
  if (!path || typeof path !== 'object') return '{}'
  const keys = Object.keys(path).sort()
  const normalized = {}
  keys.forEach((k) => {
    const val = path[k]
    if (val === undefined || val === null || val === '') return
    if (Array.isArray(val)) {
      const list = val.map((v) => String(v)).filter(Boolean).sort()
      if (list.length) normalized[k] = list
    } else {
      normalized[k] = val
    }
  })
  return JSON.stringify(normalized)
}

function cacheKey(kind, field, path) {
  return `${knownRuleVersionId ?? '0'}|${kind}|${field}|${stablePathJson(path)}`
}

/** 清空 path 级缓存（规则版本变化时调用） */
export function clearPathOptionsCache() {
  pathResultCache.clear()
  inflightRequests.clear()
}

/**
 * 同步最新规则版本；版本变化时清空大类与 path 缓存。
 * @returns {Promise<boolean>} 版本是否发生变化
 */
export async function syncRuleVersion() {
  try {
    const res = await getRuleVersionApi()
    const versionId = res.data?.id ?? null
    if (versionId !== knownRuleVersionId) {
      knownRuleVersionId = versionId
      globalLargeOptions.list = []
      globalLargeOptions.versionId = versionId
      clearPathOptionsCache()
      return true
    }
    return false
  } catch (e) {
    return false
  }
}

/**
 * 带缓存的规则 options 请求（筛选项与行内下拉共用）。
 */
export async function getCachedRuleOptions(field, path = {}) {
  const key = cacheKey('options', field, path)
  if (pathResultCache.has(key)) {
    return pathResultCache.get(key)
  }
  if (inflightRequests.has(key)) {
    return inflightRequests.get(key)
  }
  const pending = getRuleOptionsApi(field, path)
    .then((res) => {
      const data = res.data || { options: [], hint: '', input_mode: 'select' }
      pathResultCache.set(key, data)
      return data
    })
    .finally(() => {
      inflightRequests.delete(key)
    })
  inflightRequests.set(key, pending)
  return pending
}

/**
 * 带缓存的 field-meta 请求。
 */
export async function getCachedFieldMeta(field, path = {}) {
  const key = cacheKey('meta', field, path)
  if (pathResultCache.has(key)) {
    return pathResultCache.get(key)
  }
  if (inflightRequests.has(key)) {
    return inflightRequests.get(key)
  }
  const pending = getFieldMetaApi(field, path)
    .then((res) => {
      const data = res.data || { options: [], hint: '', input_mode: 'select' }
      pathResultCache.set(key, data)
      return data
    })
    .finally(() => {
      inflightRequests.delete(key)
    })
  inflightRequests.set(key, pending)
  return pending
}

/** 清空某一行已缓存的下拉选项（界面侧；path 缓存仍可复用） */
export function clearRowOptionCache(state) {
  if (!state?.options) return
  Object.keys(state.options).forEach((key) => {
    state.options[key] = []
  })
}

export function createRowCascadeState() {
  return reactive({
    options: {
      segment: [],
      type: [],
      materialMain: [],
      materialAux: [],
      packaging: [],
      size: [],
      roll: [],
      total: [],
    },
    meta: {
      materialAux: { mode: 'select', hint: '' },
      packaging: { mode: 'select', hint: '' },
      size: { mode: 'select', hint: '' },
      roll: { mode: 'select', hint: '' },
      total: { mode: 'select', hint: '' },
    },
  })
}

/** 将字段值规范为数组（界面多选绑定） */
export function normalizeMultiField(value, field) {
  if (field === 'category_segment') {
    if (Array.isArray(value)) return value.filter(Boolean)
    if (value) return [value]
    return []
  }
  if (Array.isArray(value)) return value.filter(Boolean)
  if (typeof value === 'string' && value.trim()) {
    return value.split(/[,，]/).map((s) => s.trim()).filter(Boolean)
  }
  return []
}

/** 保存到后端：区隔为数组，其余多选字段为逗号分隔字符串 */
export function serializeMultiField(value, field) {
  if (field === 'category_segment') {
    return normalizeMultiField(value, field)
  }
  return normalizeMultiField(value, field).join(',')
}

/**
 * 合并规则选项与已选手输值，避免 allow-create 的自定义值丢失展示。
 */
export function mergeSelectOptions(options, value, field) {
  const base = Array.isArray(options) ? [...options] : []
  const seen = new Set(base)
  normalizeMultiField(value, field).forEach((item) => {
    if (item && !seen.has(item)) {
      seen.add(item)
      base.push(item)
    }
  })
  return base
}

/** 占位：有规则提示用提示，否则提示可选手输 */
export function hintOrTypePlaceholder(hint) {
  const text = String(hint || '').trim()
  return text || '可选，无则输入后回车'
}

/** 规范化一行中所有分类字段（大类单选，其余多选） */
export function normalizeRowFields(row) {
  if ('category_large' in row) {
    row.category_large = normalizeSingleLarge(row.category_large)
  }
  MULTI_SELECT_FIELDS.forEach((field) => {
    if (field in row) {
      row[field] = normalizeMultiField(row[field], field)
    }
  })
  return row
}

/** 将已选值规范为路径数组（多选全部传给后端，取下级并集） */
function pathValues(value, field) {
  if (field === 'category_large') {
    const single = normalizeSingleLarge(value)
    return single ? [single] : undefined
  }
  const list = normalizeMultiField(value, field)
  return list.length ? list : undefined
}

function buildPath(row) {
  return {
    大类: pathValues(row.category_large, 'category_large'),
    区隔: pathValues(row.category_segment, 'category_segment'),
    类别: pathValues(row.category_type, 'category_type'),
    主材质: pathValues(row.material_main, 'material_main'),
    辅材质: pathValues(row.material_aux, 'material_aux'),
    包装方式: pathValues(row.packaging, 'packaging'),
    尺寸: pathValues(row.size, 'size'),
    卷数: pathValues(row.roll_count, 'roll_count'),
  }
}

export async function loadGlobalLargeOptions(force = false) {
  const versionChanged = await syncRuleVersion()
  if (!force && !versionChanged && globalLargeOptions.list.length) return
  const data = await getCachedRuleOptions('大类', {})
  globalLargeOptions.list = data.options || []
  globalLargeOptions.versionId = knownRuleVersionId
}

async function loadRowOptions(fieldKey, row, state) {
  const apiField = FIELD_API_MAP[fieldKey]
  if (!apiField) return
  const data = await getCachedRuleOptions(apiField, buildPath(row))
  const key = OPTION_KEY_MAP[fieldKey]
  state.options[key] = data.options || []
  if (fieldKey === 'material_aux') {
    state.meta.materialAux.mode = 'select'
    state.meta.materialAux.hint = data.hint || ''
    row.material_aux = normalizeMultiField(row.material_aux, 'material_aux')
  }
  if (fieldKey === 'packaging') {
    state.meta.packaging.mode = 'select'
    state.meta.packaging.hint = data.hint || ''
    row.packaging = normalizeMultiField(row.packaging, 'packaging')
  }
}

async function loadRowTailField(fieldKey, row, state) {
  const cfg = TAIL_META_MAP[fieldKey]
  if (!cfg) return
  const data = await getCachedFieldMeta(cfg.fieldName, buildPath(row))
  state.meta[cfg.targetKey].mode = 'select'
  state.meta[cfg.targetKey].hint = data.hint || ''
  row[cfg.rowField] = normalizeMultiField(row[cfg.rowField], cfg.rowField)
  state.options[cfg.optionKey] = data.options || []
}

function clearDownstream(row, fromField) {
  ;(DOWNSTREAM_CLEARS[fromField] || []).forEach((k) => {
    if (MULTI_SELECT_FIELDS.includes(k)) {
      row[k] = []
      return
    }
    row[k] = ''
  })
}

/** 清空行内下游字段的界面选项（避免改上级后仍显示旧选项） */
function clearRowDownstreamOptions(state, fromField) {
  if (!state?.options) return
  ;(DOWNSTREAM_CLEARS[fromField] || []).forEach((fieldKey) => {
    const optKey = OPTION_KEY_MAP[fieldKey]
    if (optKey) state.options[optKey] = []
  })
}

/**
 * 初始化行：仅规范化字段值，不预拉选项（懒加载）。
 */
export async function initRowCascade(row, _state) {
  normalizeRowFields(row)
}

/**
 * 某字段变更后：清空下游值与行内选项，不预拉（下次展开再请求）。
 */
export async function onRowCascadeChange(row, state, fieldKey) {
  clearDownstream(row, fieldKey)
  clearRowDownstreamOptions(state, fieldKey)
}

/** 是否经营变更 */
export async function onRowOperatingChange(row, state) {
  if (row.is_operating === '否') {
    row.category_large = ''
    MULTI_SELECT_FIELDS.forEach((k) => {
      row[k] = []
    })
    clearRowOptionCache(state)
  } else {
    await initRowCascade(row, state)
  }
}

/**
 * 兼容旧调用：按需加载单个尾部字段；未指定则加载尺寸。
 */
export async function ensureTailOptions(row, state, fieldKey = 'size') {
  if (TAIL_META_MAP[fieldKey]) {
    await loadRowTailField(fieldKey, row, state)
    return
  }
  await loadRowTailField('size', row, state)
}

/**
 * 下拉展开时加载该字段选项（优先走缓存）。
 */
export async function onDropdownVisible(row, state, fieldKey) {
  if (fieldKey === 'category_large') {
    await loadGlobalLargeOptions(false)
    return
  }
  if (TAIL_META_MAP[fieldKey]) {
    await loadRowTailField(fieldKey, row, state)
    return
  }
  if (!OPTION_KEY_MAP[fieldKey] || !FIELD_API_MAP[fieldKey]) return
  await loadRowOptions(fieldKey, row, state)
}
