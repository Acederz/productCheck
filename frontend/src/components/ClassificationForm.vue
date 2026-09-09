<template>
  <el-form :model="form" label-width="100px" class="classify-form">
    <el-form-item label="是否经营">
      <el-select v-model="form.is_operating" placeholder="请选择" clearable @change="onOperatingChange">
        <el-option label="是" value="是" />
        <el-option label="否" value="否" />
      </el-select>
    </el-form-item>

    <template v-if="form.is_operating !== '否'">
      <el-form-item label="大类">
        <el-select
          v-model="form.category_large"
          clearable
          placeholder="请选择（单选）"
          filterable
          :disabled="fieldDisabled('category_large')"
          @change="() => onCascadeChange('category_large')"
        >
          <el-option v-for="o in options.large" :key="o" :label="o" :value="o" />
        </el-select>
      </el-form-item>

      <el-form-item label="区隔">
        <el-select
          v-model="form.category_segment"
          multiple
          collapse-tags
          collapse-tags-tooltip
          placeholder="可多选"
          filterable
          :disabled="fieldDisabled('category_segment')"
          @change="() => onCascadeChange('category_segment')"
        >
          <el-option v-for="o in options.segment" :key="o" :label="o" :value="o" />
        </el-select>
      </el-form-item>

      <el-form-item label="类别">
        <el-select
          v-model="form.category_type"
          multiple
          collapse-tags
          collapse-tags-tooltip
          placeholder="请选择"
          filterable
          :disabled="fieldDisabled('category_type')"
          @change="() => onCascadeChange('category_type')"
        >
          <el-option v-for="o in options.type" :key="o" :label="o" :value="o" />
        </el-select>
      </el-form-item>

      <el-form-item label="主材质">
        <el-select
          v-model="form.material_main"
          multiple
          collapse-tags
          collapse-tags-tooltip
          placeholder="请选择"
          filterable
          :disabled="fieldDisabled('material_main')"
          @change="() => onCascadeChange('material_main')"
        >
          <el-option v-for="o in options.materialMain" :key="o" :label="o" :value="o" />
        </el-select>
      </el-form-item>

      <el-form-item label="辅材质">
        <FieldHintTooltip :hint="meta.materialAux.hint">
          <el-select
            v-model="form.material_aux"
            multiple
            collapse-tags
            collapse-tags-tooltip
            filterable
            allow-create
            default-first-option
            :placeholder="hintOrTypePlaceholder(meta.materialAux.hint)"
            :disabled="fieldDisabled('material_aux')"
            @change="() => onCascadeChange('material_aux')"
          >
            <el-option
              v-for="o in mergeSelectOptions(options.materialAux, form.material_aux, 'material_aux')"
              :key="o"
              :label="o"
              :value="o"
            />
          </el-select>
        </FieldHintTooltip>
      </el-form-item>

      <el-form-item label="包装方式">
        <FieldHintTooltip :hint="meta.packaging.hint">
          <el-select
            v-model="form.packaging"
            multiple
            collapse-tags
            collapse-tags-tooltip
            filterable
            allow-create
            default-first-option
            :placeholder="hintOrTypePlaceholder(meta.packaging.hint)"
            :disabled="fieldDisabled('packaging')"
            @change="() => onCascadeChange('packaging')"
          >
            <el-option
              v-for="o in mergeSelectOptions(options.packaging, form.packaging, 'packaging')"
              :key="o"
              :label="o"
              :value="o"
            />
          </el-select>
        </FieldHintTooltip>
      </el-form-item>

      <el-form-item label="尺寸">
        <FieldHintTooltip :hint="meta.size.hint">
          <el-select
            v-model="form.size"
            multiple
            collapse-tags
            collapse-tags-tooltip
            filterable
            allow-create
            default-first-option
            :placeholder="hintOrTypePlaceholder(meta.size.hint)"
            :disabled="fieldDisabled('size')"
            @change="() => onCascadeChange('size')"
          >
            <el-option
              v-for="o in mergeSelectOptions(options.size, form.size, 'size')"
              :key="o"
              :label="o"
              :value="o"
            />
          </el-select>
        </FieldHintTooltip>
      </el-form-item>

      <el-form-item label="卷数">
        <FieldHintTooltip :hint="meta.roll.hint">
          <el-select
            v-model="form.roll_count"
            multiple
            collapse-tags
            collapse-tags-tooltip
            filterable
            allow-create
            default-first-option
            :placeholder="hintOrTypePlaceholder(meta.roll.hint)"
            :disabled="fieldDisabled('roll_count')"
          >
            <el-option
              v-for="o in mergeSelectOptions(options.roll, form.roll_count, 'roll_count')"
              :key="o"
              :label="o"
              :value="o"
            />
          </el-select>
        </FieldHintTooltip>
      </el-form-item>

      <el-form-item label="总入数">
        <FieldHintTooltip :hint="meta.total.hint">
          <el-select
            v-model="form.total_count"
            multiple
            collapse-tags
            collapse-tags-tooltip
            filterable
            allow-create
            default-first-option
            :placeholder="hintOrTypePlaceholder(meta.total.hint)"
            :disabled="fieldDisabled('total_count')"
          >
            <el-option
              v-for="o in mergeSelectOptions(options.total, form.total_count, 'total_count')"
              :key="o"
              :label="o"
              :value="o"
            />
          </el-select>
        </FieldHintTooltip>
      </el-form-item>
    </template>
  </el-form>
</template>

<script setup>
import { reactive, watch } from 'vue'
import { getRuleOptionsApi, getFieldMetaApi } from '@/api/rules'
import {
  MULTI_SELECT_FIELDS,
  normalizeMultiField,
  normalizeRowFields,
  normalizeSingleLarge,
  mergeSelectOptions,
  hintOrTypePlaceholder,
  fetchDisabledFields,
  clearDisabledFieldValues,
  isFieldDisabled,
} from '@/composables/useClassificationCascade'
import FieldHintTooltip from '@/components/FieldHintTooltip.vue'

const props = defineProps({
  modelValue: { type: Object, required: true },
})

const emit = defineEmits(['update:modelValue', 'change'])

const form = reactive({ ...props.modelValue })

const options = reactive({
  large: [],
  segment: [],
  type: [],
  materialMain: [],
  materialAux: [],
  packaging: [],
  size: [],
  roll: [],
  total: [],
})

const meta = reactive({
  materialAux: { mode: 'select', hint: '' },
  packaging: { mode: 'select', hint: '' },
  size: { mode: 'select', hint: '' },
  roll: { mode: 'text', hint: '' },
  total: { mode: 'text', hint: '' },
})

/** 当前大类下无需填写的字段（英文名） */
const disabledFields = reactive([])

function fieldDisabled(field) {
  return isFieldDisabled(disabledFields, field)
}

async function refreshDisabledFields() {
  if (form.is_operating === '否' || !form.category_large) {
    disabledFields.splice(0, disabledFields.length)
    return
  }
  const list = await fetchDisabledFields(form.category_large)
  disabledFields.splice(0, disabledFields.length, ...list)
  clearDisabledFieldValues(form, list)
}

const cascadeOrder = [
  'category_large',
  'category_segment',
  'category_type',
  'material_main',
  'material_aux',
  'packaging',
  'size',
]

const fieldApiMap = {
  category_large: '大类',
  category_segment: '区隔',
  category_type: '类别',
  material_main: '主材质',
  material_aux: '辅材质',
  packaging: '包装方式',
}

const optionKeyMap = {
  category_large: 'large',
  category_segment: 'segment',
  category_type: 'type',
  material_main: 'materialMain',
  material_aux: 'materialAux',
  packaging: 'packaging',
}

function pathValues(value, field) {
  if (field === 'category_large') {
    const single = normalizeSingleLarge(value)
    return single ? [single] : undefined
  }
  const list = normalizeMultiField(value, field)
  return list.length ? list : undefined
}

function buildPath() {
  return {
    大类: pathValues(form.category_large, 'category_large'),
    区隔: pathValues(form.category_segment, 'category_segment'),
    类别: pathValues(form.category_type, 'category_type'),
    主材质: pathValues(form.material_main, 'material_main'),
    辅材质: pathValues(form.material_aux, 'material_aux'),
    包装方式: pathValues(form.packaging, 'packaging'),
    尺寸: pathValues(form.size, 'size'),
    卷数: pathValues(form.roll_count, 'roll_count'),
  }
}

function hasFieldValue(fieldKey) {
  if (MULTI_SELECT_FIELDS.includes(fieldKey)) {
    return normalizeMultiField(form[fieldKey], fieldKey).length > 0
  }
  return Boolean(form[fieldKey])
}

async function loadOptions(fieldKey) {
  if (fieldDisabled(fieldKey)) return
  const apiField = fieldApiMap[fieldKey]
  if (!apiField) return
  const res = await getRuleOptionsApi(apiField, buildPath())
  const key = optionKeyMap[fieldKey]
  options[key] = res.data.options || []
  if (fieldKey === 'material_aux') {
    meta.materialAux.mode = 'select'
    meta.materialAux.hint = res.data.hint || ''
    form.material_aux = normalizeMultiField(form.material_aux, 'material_aux')
  }
  if (fieldKey === 'packaging') {
    meta.packaging.mode = 'select'
    meta.packaging.hint = res.data.hint || ''
    form.packaging = normalizeMultiField(form.packaging, 'packaging')
  }
}

const tailFieldMap = { size: 'size', roll: 'roll_count', total: 'total_count' }

async function loadFieldMeta(fieldName, targetKey, optionKey) {
  const rowField = tailFieldMap[targetKey]
  if (rowField && fieldDisabled(rowField)) return
  const res = await getFieldMetaApi(fieldName, buildPath())
  meta[targetKey].mode = 'select'
  meta[targetKey].hint = res.data.hint || ''
  if (rowField) {
    form[rowField] = normalizeMultiField(form[rowField], rowField)
  }
  options[optionKey] = res.data.options || []
}

async function loadTailMeta() {
  await loadFieldMeta('尺寸', 'size', 'size')
  await loadFieldMeta('卷数', 'roll', 'roll')
  await loadFieldMeta('总入数', 'total', 'total')
}

function clearDownstream(fromField) {
  const idx = cascadeOrder.indexOf(fromField)
  if (idx < 0) return
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
    if (MULTI_SELECT_FIELDS.includes(k)) form[k] = []
    else form[k] = ''
  })
}

async function onCascadeChange(fieldKey) {
  clearDownstream(fieldKey)
  if (fieldKey === 'category_large') {
    await refreshDisabledFields()
  }
  const idx = cascadeOrder.indexOf(fieldKey)
  const toLoad = cascadeOrder.slice(idx + 1)
  for (const key of toLoad) {
    if (fieldApiMap[key]) await loadOptions(key)
  }
  await loadTailMeta()
  emitChange()
}

function onOperatingChange() {
  if (form.is_operating === '否') {
    form.category_large = ''
    MULTI_SELECT_FIELDS.forEach((k) => {
      form[k] = []
    })
    disabledFields.splice(0, disabledFields.length)
  } else {
    initOptions()
  }
  emitChange()
}

function emitChange() {
  emit('update:modelValue', { ...form })
  emit('change', { ...form })
}

async function initOptions() {
  normalizeRowFields(form)
  await loadOptions('category_large')
  if (hasFieldValue('category_large')) {
    await refreshDisabledFields()
    for (const key of cascadeOrder.slice(1)) {
      if (fieldApiMap[key] && (hasFieldValue(key) || key === 'category_segment')) {
        await loadOptions(key)
      }
    }
    await loadTailMeta()
  }
}

watch(
  () => props.modelValue,
  (val) => {
    Object.assign(form, val)
    normalizeRowFields(form)
    initOptions()
  },
  { immediate: true, deep: true }
)
</script>

<style scoped>
.classify-form {
  max-width: 560px;
}
</style>
