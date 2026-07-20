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
          multiple
          collapse-tags
          collapse-tags-tooltip
          placeholder="请选择"
          filterable
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
          @change="() => onCascadeChange('material_main')"
        >
          <el-option v-for="o in options.materialMain" :key="o" :label="o" :value="o" />
        </el-select>
      </el-form-item>

      <el-form-item label="辅材质">
        <el-select
          v-if="meta.materialAux.mode === 'select'"
          v-model="form.material_aux"
          multiple
          collapse-tags
          collapse-tags-tooltip
          :placeholder="meta.materialAux.hint"
          filterable
          @change="() => onCascadeChange('material_aux')"
        >
          <el-option v-for="o in options.materialAux" :key="o" :label="o" :value="o" />
        </el-select>
        <el-input
          v-else
          v-model="form.material_aux"
          :placeholder="meta.materialAux.hint"
          @change="() => onCascadeChange('material_aux')"
        />
      </el-form-item>

      <el-form-item label="包装方式">
        <el-select
          v-if="meta.packaging.mode === 'select'"
          v-model="form.packaging"
          multiple
          collapse-tags
          collapse-tags-tooltip
          :placeholder="meta.packaging.hint"
          filterable
          @change="() => onCascadeChange('packaging')"
        >
          <el-option v-for="o in options.packaging" :key="o" :label="o" :value="o" />
        </el-select>
        <el-input
          v-else
          v-model="form.packaging"
          :placeholder="meta.packaging.hint"
          @change="() => onCascadeChange('packaging')"
        />
      </el-form-item>

      <el-form-item label="尺寸">
        <el-select
          v-if="meta.size.mode === 'select'"
          v-model="form.size"
          multiple
          collapse-tags
          collapse-tags-tooltip
          :placeholder="meta.size.hint"
          filterable
          @change="() => onCascadeChange('size')"
        >
          <el-option v-for="o in options.size" :key="o" :label="o" :value="o" />
        </el-select>
        <el-input
          v-else
          v-model="form.size"
          :placeholder="meta.size.hint"
          @change="() => onCascadeChange('size')"
        />
      </el-form-item>

      <el-form-item label="卷数">
        <el-select
          v-if="meta.roll.mode === 'select'"
          v-model="form.roll_count"
          multiple
          collapse-tags
          collapse-tags-tooltip
          :placeholder="meta.roll.hint"
          filterable
        >
          <el-option v-for="o in options.roll" :key="o" :label="o" :value="o" />
        </el-select>
        <el-input v-else v-model="form.roll_count" :placeholder="meta.roll.hint" />
      </el-form-item>

      <el-form-item label="总入数">
        <el-select
          v-if="meta.total.mode === 'select'"
          v-model="form.total_count"
          multiple
          collapse-tags
          collapse-tags-tooltip
          :placeholder="meta.total.hint"
          filterable
        >
          <el-option v-for="o in options.total" :key="o" :label="o" :value="o" />
        </el-select>
        <el-input v-else v-model="form.total_count" :placeholder="meta.total.hint" />
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
} from '@/composables/useClassificationCascade'

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

function firstPathValue(value) {
  const list = normalizeMultiField(value, 'category_large')
  return list.length ? list[0] : undefined
}

function buildPath() {
  return {
    大类: firstPathValue(form.category_large),
    区隔: form.category_segment?.length ? form.category_segment : undefined,
    类别: firstPathValue(form.category_type),
    主材质: firstPathValue(form.material_main),
    辅材质: firstPathValue(form.material_aux),
    包装方式: firstPathValue(form.packaging),
    尺寸: firstPathValue(form.size),
    卷数: firstPathValue(form.roll_count),
  }
}

function hasFieldValue(fieldKey) {
  if (MULTI_SELECT_FIELDS.includes(fieldKey)) {
    return normalizeMultiField(form[fieldKey], fieldKey).length > 0
  }
  return Boolean(form[fieldKey])
}

async function loadOptions(fieldKey) {
  const apiField = fieldApiMap[fieldKey]
  if (!apiField) return
  const res = await getRuleOptionsApi(apiField, buildPath())
  const key = optionKeyMap[fieldKey]
  options[key] = res.data.options || []
  if (fieldKey === 'material_aux') {
    meta.materialAux.mode = res.data.input_mode === 'text' ? 'text' : 'select'
    meta.materialAux.hint = res.data.hint || ''
    if (meta.materialAux.mode === 'select') {
      form.material_aux = normalizeMultiField(form.material_aux, 'material_aux')
    }
  }
  if (fieldKey === 'packaging') {
    meta.packaging.mode = res.data.input_mode === 'text' ? 'text' : 'select'
    meta.packaging.hint = res.data.hint || ''
    if (meta.packaging.mode === 'select') {
      form.packaging = normalizeMultiField(form.packaging, 'packaging')
    }
  }
}

const tailFieldMap = { size: 'size', roll: 'roll_count', total: 'total_count' }

async function loadFieldMeta(fieldName, targetKey, optionKey) {
  const res = await getFieldMetaApi(fieldName, buildPath())
  meta[targetKey].mode = res.data.input_mode === 'select' ? 'select' : 'text'
  meta[targetKey].hint = res.data.hint || ''
  const rowField = tailFieldMap[targetKey]
  if (rowField && res.data.input_mode === 'select') {
    form[rowField] = normalizeMultiField(form[rowField], rowField)
  }
  if (res.data.input_mode === 'select') {
    options[optionKey] = res.data.options || []
  }
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
    MULTI_SELECT_FIELDS.forEach((k) => {
      form[k] = []
    })
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
