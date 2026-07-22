/**
 * 分类字段级联逻辑（操作员行内编辑复用）
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
}

/** 所有分类下拉字段（除「是否经营」外）均支持多选 */
export const MULTI_SELECT_FIELDS = [
  'category_large',
  'category_segment',
  'category_type',
  'material_main',
  'material_aux',
  'packaging',
  'size',
  'roll_count',
  'total_count',
]

/** 全局大类选项（所有行共用；规则版本变化时自动刷新） */
export const globalLargeOptions = reactive({ list: [], versionId: null })

/** 前端已知的最新规则版本 id */
let knownRuleVersionId = null

/**
 * 同步最新规则版本；版本变化时清空大类缓存。
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
      return true
    }
    return false
  } catch (e) {
    return false
  }
}

/** 清空某一行已缓存的下拉选项（强制下次重新请求最新规则） */
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
      roll: { mode: 'text', hint: '' },
      total: { mode: 'text', hint: '' },
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

/** 规范化一行中所有多选字段 */
export function normalizeRowFields(row) {
  MULTI_SELECT_FIELDS.forEach((field) => {
    if (field in row) {
      row[field] = normalizeMultiField(row[field], field)
    }
  })
  return row
}

/** 将已选值规范为路径数组（多选全部传给后端，取下级并集） */
function pathValues(value, field) {
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
  // 规则版本变了，或强制刷新，或尚未加载时，重新请求大类
  const versionChanged = await syncRuleVersion()
  if (!force && !versionChanged && globalLargeOptions.list.length) return
  const res = await getRuleOptionsApi('大类', {})
  globalLargeOptions.list = res.data.options || []
  globalLargeOptions.versionId = knownRuleVersionId
}

async function loadRowOptions(fieldKey, row, state) {
  const apiField = FIELD_API_MAP[fieldKey]
  if (!apiField) return
  const res = await getRuleOptionsApi(apiField, buildPath(row))
  const key = OPTION_KEY_MAP[fieldKey]
  state.options[key] = res.data.options || []
  if (fieldKey === 'material_aux') {
    state.meta.materialAux.mode = res.data.input_mode === 'text' ? 'text' : 'select'
    state.meta.materialAux.hint = res.data.hint || ''
    if (state.meta.materialAux.mode === 'select') {
      row.material_aux = normalizeMultiField(row.material_aux, 'material_aux')
    }
  }
  if (fieldKey === 'packaging') {
    state.meta.packaging.mode = res.data.input_mode === 'text' ? 'text' : 'select'
    state.meta.packaging.hint = res.data.hint || ''
    if (state.meta.packaging.mode === 'select') {
      row.packaging = normalizeMultiField(row.packaging, 'packaging')
    }
  }
}

const TAIL_FIELD_MAP = {
  size: 'size',
  roll: 'roll_count',
  total: 'total_count',
}

async function loadRowFieldMeta(fieldName, targetKey, optionKey, row, state) {
  const res = await getFieldMetaApi(fieldName, buildPath(row))
  state.meta[targetKey].mode = res.data.input_mode === 'select' ? 'select' : 'text'
  state.meta[targetKey].hint = res.data.hint || ''
  const rowField = TAIL_FIELD_MAP[targetKey]
  if (rowField && res.data.input_mode === 'select') {
    row[rowField] = normalizeMultiField(row[rowField], rowField)
  }
  if (res.data.input_mode === 'select') {
    state.options[optionKey] = res.data.options || []
  }
}

async function loadRowTailMeta(row, state) {
  await loadRowFieldMeta('尺寸', 'size', 'size', row, state)
  await loadRowFieldMeta('卷数', 'roll', 'roll', row, state)
  await loadRowFieldMeta('总入数', 'total', 'total', row, state)
}

function clearDownstream(row, fromField) {
  const clears = {
    category_large: ['category_segment', 'category_type', 'material_main', 'material_aux', 'packaging', 'size', 'roll_count', 'total_count'],
    category_segment: ['category_type', 'material_main', 'material_aux', 'packaging', 'size', 'roll_count', 'total_count'],
    category_type: ['material_main', 'material_aux', 'packaging', 'size', 'roll_count', 'total_count'],
    material_main: ['material_aux', 'packaging', 'size', 'roll_count', 'total_count'],
    material_aux: ['packaging', 'size', 'roll_count', 'total_count'],
    packaging: ['size', 'roll_count', 'total_count'],
    size: ['roll_count', 'total_count'],
  }
  ;(clears[fromField] || []).forEach((k) => {
    if (MULTI_SELECT_FIELDS.includes(k)) {
      row[k] = []
      return
    }
    row[k] = ''
  })
}

function hasFieldValue(row, fieldKey) {
  if (MULTI_SELECT_FIELDS.includes(fieldKey)) {
    return normalizeMultiField(row[fieldKey], fieldKey).length > 0
  }
  return Boolean(row[fieldKey])
}

/** 初始化某一行的级联选项（已有值时恢复下拉列表） */
export async function initRowCascade(row, state) {
  normalizeRowFields(row)
  if (!hasFieldValue(row, 'category_large')) return
  for (const key of CASCADE_ORDER.slice(1)) {
    if (hasFieldValue(row, key) || key === 'category_segment') {
      await loadRowOptions(key, row, state)
    }
  }
  await loadRowTailMeta(row, state)
}

/** 某字段变更后刷新下游选项 */
export async function onRowCascadeChange(row, state, fieldKey) {
  clearDownstream(row, fieldKey)
  const idx = CASCADE_ORDER.indexOf(fieldKey)
  const toLoad = CASCADE_ORDER.slice(idx + 1)
  for (const key of toLoad) {
    if (FIELD_API_MAP[key]) await loadRowOptions(key, row, state)
  }
  await loadRowTailMeta(row, state)
}

/** 是否经营变更 */
export async function onRowOperatingChange(row, state) {
  if (row.is_operating === '否') {
    MULTI_SELECT_FIELDS.forEach((k) => {
      row[k] = []
    })
  } else {
    await initRowCascade(row, state)
  }
}

export async function ensureTailOptions(row, state) {
  await loadRowTailMeta(row, state)
}

/** 下拉展开时加载选项（始终向服务器要最新规则，避免导入新规则后仍显示旧选项） */
export async function onDropdownVisible(row, state, fieldKey) {
  if (fieldKey === 'category_large') {
    await loadGlobalLargeOptions(true)
    return
  }
  const key = OPTION_KEY_MAP[fieldKey]
  if (!key) return
  await loadRowOptions(fieldKey, row, state)
}
