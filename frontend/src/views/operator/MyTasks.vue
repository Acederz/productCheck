<template>
  <div class="my-tasks-page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>我的任务</span>
          <el-button
            type="primary"
            :disabled="!selectedIds.length"
            @click="handleBatchSubmit"
          >
            批量提交 ({{ selectedIds.length }})
          </el-button>
        </div>
      </template>

      <el-form :inline="true" :model="filters" class="filter-form" @submit.prevent>
        <el-form-item label="状态">
          <el-select
            v-model="filters.status"
            multiple
            collapse-tags
            collapse-tags-tooltip
            clearable
            placeholder="全部"
            style="width: 150px"
          >
            <el-option v-for="s in statusOptions" :key="s" :label="s" :value="s" />
          </el-select>
        </el-form-item>
        <el-form-item label="平台">
          <el-select
            v-model="filters.platform"
            multiple
            collapse-tags
            collapse-tags-tooltip
            clearable
            placeholder="全部"
            style="width: 180px"
          >
            <el-option v-for="p in platformOptions" :key="p" :label="p" :value="p" />
          </el-select>
        </el-form-item>
        <el-form-item label="关键词">
          <el-input
            v-model="filters.keyword"
            placeholder="宝贝ID / 名称"
            clearable
            style="width: 180px"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>

      <div class="table-wrap">
        <el-table
          :data="tableData"
          v-loading="loading"
          border
          stripe
          size="small"
          @selection-change="onSelectionChange"
        >
          <el-table-column type="selection" width="45" fixed="left" />
          <el-table-column prop="product_id" label="宝贝ID" width="130" fixed="left" />
          <el-table-column prop="product_name" label="宝贝名称" width="160" fixed="left" show-overflow-tooltip />
          <el-table-column prop="platform" label="平台" width="110" />
          <el-table-column prop="status" label="状态" width="80" />
          <el-table-column label="驳回原因" width="120" show-overflow-tooltip>
            <template #default="{ row }">{{ row.reject_reason || '-' }}</template>
          </el-table-column>

          <!-- 展示字段：主图 / 产品属性 / 宝贝文描图 -->
          <el-table-column label="主图" width="90">
            <template #default="{ row }">
              <el-popover
                v-if="row.main_image"
                placement="right-start"
                :width="360"
                trigger="hover"
                :show-after="150"
                :hide-after="80"
                popper-class="main-image-popover"
              >
                <template #reference>
                  <img
                    :src="row.main_image"
                    alt="主图"
                    class="main-image-thumb"
                    loading="lazy"
                  />
                </template>
                <img :src="row.main_image" alt="主图预览" class="main-image-hover-preview" />
              </el-popover>
              <span v-else>-</span>
            </template>
          </el-table-column>

          <el-table-column label="产品属性" width="220">
            <template #default="{ row }">
              <div class="product-attr-cell" :title="formatProductAttr(row.product_attr)">
                {{ formatProductAttr(row.product_attr) }}
              </div>
            </template>
          </el-table-column>

          <el-table-column label="宝贝文描图" width="170">
            <template #default="{ row }">
              <el-button
                link
                type="primary"
                size="small"
                :disabled="getDescCount(row) === 0"
                @click="openDescViewer(row)"
              >
                查看({{ getDescCount(row) }})
              </el-button>
            </template>
          </el-table-column>

          <!-- 可编辑分类字段（行内直接填写） -->
          <el-table-column label="是否经营" width="100">
            <template #default="{ row }">
              <el-select
                v-model="row.is_operating"
                placeholder="选择"
                size="small"
                clearable
                @change="() => handleOperatingChange(row)"
              >
                <el-option label="是" value="是" />
                <el-option label="否" value="否" />
              </el-select>
            </template>
          </el-table-column>

          <el-table-column label="大类" width="140">
              <template #default="{ row }">
                <el-select
                  v-model="row.category_large"
                  multiple
                  collapse-tags
                  collapse-tags-tooltip
                  placeholder="大类"
                  size="small"
                  filterable
                  :disabled="row.is_operating === '否'"
                  @visible-change="(v) => v && onDropdownVisible(row, 'category_large')"
                  @change="() => handleCascadeChange(row, 'category_large')"
                >
                  <el-option v-for="o in globalLargeOptions.list" :key="o" :label="o" :value="o" />
                </el-select>
              </template>
            </el-table-column>

            <el-table-column label="区隔" width="140">
              <template #default="{ row }">
                <el-select
                  v-model="row.category_segment"
                  multiple
                  collapse-tags
                  collapse-tags-tooltip
                  placeholder="区隔"
                  size="small"
                  filterable
                  :disabled="row.is_operating === '否'"
                  @visible-change="(v) => v && onDropdownVisible(row, 'category_segment')"
                  @change="() => handleCascadeChange(row, 'category_segment')"
                >
                  <el-option
                    v-for="o in getRowState(row.id).options.segment"
                    :key="o"
                    :label="o"
                    :value="o"
                  />
                </el-select>
              </template>
            </el-table-column>

            <el-table-column label="类别" width="140">
              <template #default="{ row }">
                <el-select
                  v-model="row.category_type"
                  multiple
                  collapse-tags
                  collapse-tags-tooltip
                  placeholder="类别"
                  size="small"
                  filterable
                  :disabled="row.is_operating === '否'"
                  @visible-change="(v) => v && onDropdownVisible(row, 'category_type')"
                  @change="() => handleCascadeChange(row, 'category_type')"
                >
                  <el-option v-for="o in getRowState(row.id).options.type" :key="o" :label="o" :value="o" />
                </el-select>
              </template>
            </el-table-column>

            <el-table-column label="主材质" width="140">
              <template #default="{ row }">
                <el-select
                  v-model="row.material_main"
                  multiple
                  collapse-tags
                  collapse-tags-tooltip
                  placeholder="主材质"
                  size="small"
                  filterable
                  :disabled="row.is_operating === '否'"
                  @visible-change="(v) => v && onDropdownVisible(row, 'material_main')"
                  @change="() => handleCascadeChange(row, 'material_main')"
                >
                  <el-option
                    v-for="o in getRowState(row.id).options.materialMain"
                    :key="o"
                    :label="o"
                    :value="o"
                  />
                </el-select>
              </template>
            </el-table-column>

            <el-table-column label="辅材质" width="140">
              <template #default="{ row }">
                <el-select
                  v-if="getRowState(row.id).meta.materialAux.mode === 'select'"
                  v-model="row.material_aux"
                  multiple
                  collapse-tags
                  collapse-tags-tooltip
                  :placeholder="getRowState(row.id).meta.materialAux.hint"
                  size="small"
                  filterable
                  :disabled="row.is_operating === '否'"
                  @visible-change="(v) => v && onDropdownVisible(row, 'material_aux')"
                  @change="() => handleCascadeChange(row, 'material_aux')"
                >
                  <el-option
                    v-for="o in getRowState(row.id).options.materialAux"
                    :key="o"
                    :label="o"
                    :value="o"
                  />
                </el-select>
                <el-input
                  v-else
                  v-model="row.material_aux"
                  size="small"
                  :placeholder="getRowState(row.id).meta.materialAux.hint"
                  :disabled="row.is_operating === '否'"
                  @change="() => scheduleDraft(row)"
                />
              </template>
            </el-table-column>

            <el-table-column label="包装方式" width="140">
              <template #default="{ row }">
                <el-select
                  v-if="getRowState(row.id).meta.packaging.mode === 'select'"
                  v-model="row.packaging"
                  multiple
                  collapse-tags
                  collapse-tags-tooltip
                  :placeholder="getRowState(row.id).meta.packaging.hint"
                  size="small"
                  filterable
                  :disabled="row.is_operating === '否'"
                  @visible-change="(v) => v && onDropdownVisible(row, 'packaging')"
                  @change="() => handleCascadeChange(row, 'packaging')"
                >
                  <el-option
                    v-for="o in getRowState(row.id).options.packaging"
                    :key="o"
                    :label="o"
                    :value="o"
                  />
                </el-select>
                <el-input
                  v-else
                  v-model="row.packaging"
                  size="small"
                  :placeholder="getRowState(row.id).meta.packaging.hint"
                  :disabled="row.is_operating === '否'"
                  @change="() => scheduleDraft(row)"
                />
              </template>
            </el-table-column>

            <el-table-column label="尺寸" width="150">
              <template #default="{ row }">
                <el-select
                  v-if="getRowState(row.id).meta.size.mode === 'select'"
                  v-model="row.size"
                  multiple
                  collapse-tags
                  collapse-tags-tooltip
                  :placeholder="getRowState(row.id).meta.size.hint"
                  size="small"
                  filterable
                  :disabled="row.is_operating === '否'"
                  @visible-change="(v) => v && ensureTailOptions(row, getRowState(row.id))"
                  @change="() => handleCascadeChange(row, 'size')"
                >
                  <el-option v-for="o in getRowState(row.id).options.size" :key="o" :label="o" :value="o" />
                </el-select>
                <el-input
                  v-else
                  v-model="row.size"
                  size="small"
                  :placeholder="getRowState(row.id).meta.size.hint"
                  :disabled="row.is_operating === '否'"
                  @change="() => scheduleDraft(row)"
                />
              </template>
            </el-table-column>

            <el-table-column label="卷数" width="110">
              <template #default="{ row }">
                <el-select
                  v-if="getRowState(row.id).meta.roll.mode === 'select'"
                  v-model="row.roll_count"
                  multiple
                  collapse-tags
                  collapse-tags-tooltip
                  :placeholder="getRowState(row.id).meta.roll.hint"
                  size="small"
                  filterable
                  :disabled="row.is_operating === '否'"
                  @visible-change="(v) => v && ensureTailOptions(row, getRowState(row.id))"
                >
                  <el-option v-for="o in getRowState(row.id).options.roll" :key="o" :label="o" :value="o" />
                </el-select>
                <el-input
                  v-else
                  v-model="row.roll_count"
                  size="small"
                  :placeholder="getRowState(row.id).meta.roll.hint"
                  :disabled="row.is_operating === '否'"
                  @change="() => scheduleDraft(row)"
                />
              </template>
            </el-table-column>

            <el-table-column label="总入数" width="110">
              <template #default="{ row }">
                <el-select
                  v-if="getRowState(row.id).meta.total.mode === 'select'"
                  v-model="row.total_count"
                  multiple
                  collapse-tags
                  collapse-tags-tooltip
                  :placeholder="getRowState(row.id).meta.total.hint"
                  size="small"
                  filterable
                  :disabled="row.is_operating === '否'"
                  @visible-change="(v) => v && ensureTailOptions(row, getRowState(row.id))"
                >
                  <el-option v-for="o in getRowState(row.id).options.total" :key="o" :label="o" :value="o" />
                </el-select>
                <el-input
                  v-else
                  v-model="row.total_count"
                  size="small"
                  :placeholder="getRowState(row.id).meta.total.hint"
                  :disabled="row.is_operating === '否'"
                  @change="() => scheduleDraft(row)"
                />
              </template>
            </el-table-column>

          <el-table-column label="操作" width="130" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="handleSaveRow(row)">保存</el-button>
              <el-button link type="success" size="small" @click="handleSubmitRow(row)">提交</el-button>
              <el-tag v-if="draftFlags[row.id]" type="success" size="small" class="draft-tag">暂存</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        class="table-pagination"
        @current-change="loadTasks"
        @size-change="handlePageSizeChange"
      />
    </el-card>

    <!-- 宝贝文描图灯箱：支持切换、滚轮缩放与拖拽平移 -->
    <el-dialog
      v-model="descViewerVisible"
      title="宝贝文描图"
      width="1000px"
      class="desc-viewer-dialog"
      align-center
      destroy-on-close
      :close-on-click-modal="false"
      @closed="resetDescViewer"
    >
      <div v-if="descViewerImages.length" class="desc-viewer">
        <div class="desc-viewer-toolbar">
          <span>{{ descViewerIndex + 1 }} / {{ descViewerImages.length }}</span>
          <span class="desc-viewer-tip">滚轮放大/缩小，放大后可拖拽查看细节</span>
          <div class="desc-viewer-actions">
            <el-button size="small" @click="zoomDescOut">缩小</el-button>
            <span class="desc-zoom-text">{{ Math.round(descZoomScale * 100) }}%</span>
            <el-button size="small" @click="zoomDescIn">放大</el-button>
            <el-button size="small" @click="resetDescTransform">重置</el-button>
          </div>
        </div>

        <div
          class="desc-viewer-stage"
          :class="{
            'is-draggable': descZoomScale > 1,
            'is-dragging': descDragging,
          }"
          @wheel.prevent="onDescWheel"
          @mousedown="onDescMouseDown"
        >
          <img
            v-if="descViewerImages[descViewerIndex]"
            :src="descViewerImages[descViewerIndex]"
            alt="文描图"
            class="desc-viewer-image"
            :style="descImageStyle"
            draggable="false"
          />
        </div>

        <div class="desc-viewer-nav">
          <el-button :disabled="descViewerIndex <= 0" @click="showPrevDesc">上一张</el-button>
          <el-button
            :disabled="descViewerIndex >= descViewerImages.length - 1"
            @click="showNextDesc"
          >
            下一张
          </el-button>
        </div>
      </div>
      <div v-else class="empty-viewer">暂无图片</div>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  createRowCascadeState,
  globalLargeOptions,
  initRowCascade,
  loadGlobalLargeOptions,
  onDropdownVisible as loadDropdownOptions,
  onRowCascadeChange,
  onRowOperatingChange,
  ensureTailOptions,
  MULTI_SELECT_FIELDS,
  normalizeRowFields,
  serializeMultiField,
} from '@/composables/useClassificationCascade'
import { myTasksApi, saveDraftApi, submitTasksApi, updateTaskApi } from '@/api/tasks'
import { useUserStore } from '@/stores/user'

const loading = ref(false)
const tableData = ref([])
const selectedIds = ref([])
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const rowStates = reactive({})
const draftFlags = reactive({})
const draftTimers = {}
const userStore = useUserStore()

const statusOptions = ['待处理', '已驳回']
const platformOptions = ['淘宝', '京东', '消费者洞察淘宝', '消费者洞察京东']
const filters = reactive({
  status: [],
  platform: [],
  keyword: '',
})

/** 多选筛选项：未选或全选视为「全部」，不传查询参数 */
function resolveFilterValues(selected, allOptions) {
  if (!selected?.length) return undefined
  if (
    selected.length >= allOptions.length
    && allOptions.every((item) => selected.includes(item))
  ) {
    return undefined
  }
  return selected.join(',')
}

const descViewerVisible = ref(false)
const descViewerImages = ref([])
const descViewerIndex = ref(0)
const descZoomScale = ref(1)
const descPanX = ref(0)
const descPanY = ref(0)
const descDragging = ref(false)

const DESC_ZOOM_MIN = 0.5
const DESC_ZOOM_MAX = 4
const DESC_ZOOM_STEP = 0.12

const descDragStart = {
  x: 0,
  y: 0,
  panX: 0,
  panY: 0,
}

const descImageStyle = computed(() => ({
  transform: `translate(${descPanX.value}px, ${descPanY.value}px) scale(${descZoomScale.value})`,
}))

function getRowState(taskId) {
  if (!rowStates[taskId]) {
    rowStates[taskId] = createRowCascadeState()
  }
  return rowStates[taskId]
}

function normalizeDescImages(descImages) {
  // 数据可能是 JSON 数组，也可能是旧数据字符串（JSON 或逗号分隔）。
  if (Array.isArray(descImages)) {
    return descImages.filter(Boolean)
  }
  if (typeof descImages === 'string') {
    const raw = descImages.trim()
    if (!raw) return []
    try {
      const parsed = JSON.parse(raw)
      if (Array.isArray(parsed)) return parsed.filter(Boolean)
    } catch (e) {
      // 非 JSON，按分隔符拆分
    }
    return raw
      .split(/[,\n;；\s]+/)
      .map((s) => s.trim())
      .filter(Boolean)
  }
  return []
}

function getDescCount(row) {
  return normalizeDescImages(row?.desc_images).length
}

function resetDescTransform() {
  descZoomScale.value = 1
  descPanX.value = 0
  descPanY.value = 0
  stopDescDrag()
}

function resetDescViewer() {
  descViewerImages.value = []
  descViewerIndex.value = 0
  resetDescTransform()
}

function stopDescDrag() {
  descDragging.value = false
  window.removeEventListener('mousemove', onDescMouseMove)
  window.removeEventListener('mouseup', onDescMouseUp)
}

function clampDescZoom(value) {
  return Math.min(DESC_ZOOM_MAX, Math.max(DESC_ZOOM_MIN, value))
}

function applyDescZoom(delta) {
  const next = clampDescZoom(Number((descZoomScale.value + delta).toFixed(2)))
  descZoomScale.value = next
  // 缩放回 100% 及以下时，自动归位
  if (next <= 1) {
    descPanX.value = 0
    descPanY.value = 0
  }
}

function zoomDescIn() {
  applyDescZoom(DESC_ZOOM_STEP)
}

function zoomDescOut() {
  applyDescZoom(-DESC_ZOOM_STEP)
}

function onDescWheel(event) {
  const delta = event.deltaY < 0 ? DESC_ZOOM_STEP : -DESC_ZOOM_STEP
  applyDescZoom(delta)
}

function onDescMouseDown(event) {
  // 仅放大后允许拖拽平移
  if (descZoomScale.value <= 1 || event.button !== 0) return
  descDragging.value = true
  descDragStart.x = event.clientX
  descDragStart.y = event.clientY
  descDragStart.panX = descPanX.value
  descDragStart.panY = descPanY.value
  window.addEventListener('mousemove', onDescMouseMove)
  window.addEventListener('mouseup', onDescMouseUp)
}

function onDescMouseMove(event) {
  if (!descDragging.value) return
  descPanX.value = descDragStart.panX + (event.clientX - descDragStart.x)
  descPanY.value = descDragStart.panY + (event.clientY - descDragStart.y)
}

function onDescMouseUp() {
  stopDescDrag()
}

function showPrevDesc() {
  if (descViewerIndex.value <= 0) return
  descViewerIndex.value -= 1
  resetDescTransform()
}

function showNextDesc() {
  if (descViewerIndex.value >= descViewerImages.value.length - 1) return
  descViewerIndex.value += 1
  resetDescTransform()
}

function openDescViewer(row) {
  descViewerImages.value = normalizeDescImages(row?.desc_images)
  descViewerIndex.value = 0
  resetDescTransform()
  descViewerVisible.value = true
}

function formatProductAttr(val) {
  if (val === null || val === undefined) return '-'
  if (typeof val === 'string') {
    const s = val.trim()
    return s ? s : '-'
  }
  if (Array.isArray(val)) return val.join('；')
  try {
    return JSON.stringify(val)
  } catch (e) {
    return String(val)
  }
}

function pickEditable(row) {
  const data = { is_operating: row.is_operating || '' }
  MULTI_SELECT_FIELDS.forEach((field) => {
    data[field] = serializeMultiField(row[field], field)
  })
  return data
}

function normalizeRow(row) {
  normalizeRowFields(row)
  row.desc_images = normalizeDescImages(row.desc_images)
  return row
}

function onSelectionChange(rows) {
  selectedIds.value = rows.map((r) => r.id)
}

async function onDropdownVisible(row, fieldKey) {
  await loadDropdownOptions(row, getRowState(row.id), fieldKey)
}

async function handleCascadeChange(row, fieldKey) {
  await onRowCascadeChange(row, getRowState(row.id), fieldKey)
  scheduleDraft(row)
}

async function handleOperatingChange(row) {
  await onRowOperatingChange(row, getRowState(row.id))
  scheduleDraft(row)
}

function scheduleDraft(row) {
  clearTimeout(draftTimers[row.id])
  draftTimers[row.id] = setTimeout(async () => {
    try {
      const data = pickEditable(row)
      await saveDraftApi(row.id, data)
      localStorage.setItem(`draft_${userStore.user.id}_${row.id}`, JSON.stringify(data))
      draftFlags[row.id] = true
    } catch (e) {
      /* 静默，可手动保存 */
    }
  }, 800)
}

function buildQueryParams() {
  return {
    page: page.value,
    page_size: pageSize.value,
    status: resolveFilterValues(filters.status, statusOptions),
    platform: resolveFilterValues(filters.platform, platformOptions),
    keyword: filters.keyword?.trim() || undefined,
  }
}

function handleSearch() {
  page.value = 1
  loadTasks()
}

function handleReset() {
  filters.status = []
  filters.platform = []
  filters.keyword = ''
  page.value = 1
  loadTasks()
}

function handlePageSizeChange() {
  page.value = 1
  loadTasks()
}

async function loadTasks() {
  loading.value = true
  try {
    const res = await myTasksApi(buildQueryParams())
    const items = (res.data.items || []).map(normalizeRow)
    tableData.value = items
    total.value = res.data.total || 0
    await loadGlobalLargeOptions()
    for (const row of items) {
      await initRowCascade(row, getRowState(row.id))
    }
  } finally {
    loading.value = false
  }
}

async function handleSaveRow(row) {
  await updateTaskApi(row.id, pickEditable(row))
  draftFlags[row.id] = false
  ElMessage.success('保存成功')
}

async function handleSubmitRow(row) {
  await updateTaskApi(row.id, pickEditable(row))
  const res = await submitTasksApi([row.id])
  if (res.data.skipped?.length) {
    ElMessage.warning(res.data.skipped[0].reason)
    return
  }
  ElMessage.success('提交成功')
  draftFlags[row.id] = false
  await loadTasks()
}

async function handleBatchSubmit() {
  const res = await submitTasksApi(selectedIds.value)
  const ok = res.data.success_ids?.length || 0
  const skip = res.data.skipped?.length || 0
  ElMessage.success(`提交完成：成功 ${ok} 条，跳过 ${skip} 条`)
  await loadTasks()
}

onMounted(async () => {
  await loadGlobalLargeOptions()
  await loadTasks()
})
onUnmounted(stopDescDrag)
</script>

<style scoped>
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.filter-form {
  margin-bottom: 12px;
}
.table-pagination {
  margin-top: 16px;
  justify-content: flex-end;
}
.table-wrap {
  width: 100%;
  overflow-x: auto;
}
.my-tasks-page :deep(.el-select) {
  width: 100%;
}
.draft-tag {
  margin-left: 4px;
}

.main-image-thumb {
  width: 60px;
  height: 60px;
  object-fit: cover;
  border-radius: 4px;
  cursor: zoom-in;
  display: block;
}

.main-image-hover-preview {
  display: block;
  width: 100%;
  max-height: 420px;
  object-fit: contain;
}

.product-attr-cell {
  white-space: normal;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  line-height: 1.4;
}

.desc-viewer-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
  color: #606266;
  font-size: 13px;
  flex-shrink: 0;
}

.desc-viewer-tip {
  flex: 1;
  color: #909399;
}

.desc-viewer-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.desc-zoom-text {
  min-width: 48px;
  text-align: center;
  color: #303133;
}

.desc-viewer-stage {
  height: calc(100vh - 260px);
  max-height: 560px;
  min-height: 300px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background: #fafafa;
  border-radius: 8px;
  border: 1px solid #ebeef5;
}

.desc-viewer-stage.is-draggable {
  cursor: grab;
}

.desc-viewer-stage.is-dragging {
  cursor: grabbing;
}

.desc-viewer-image {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  transform-origin: center center;
  transition: transform 0.06s ease-out;
  user-select: none;
  pointer-events: none;
}

.desc-viewer-stage.is-dragging .desc-viewer-image {
  transition: none;
}

.desc-viewer-nav {
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-top: 10px;
  flex-shrink: 0;
}

.empty-viewer {
  height: calc(100vh - 260px);
  max-height: 560px;
  min-height: 300px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #909399;
  background: #fafafa;
  border-radius: 8px;
}
</style>

<style>
.main-image-popover {
  padding: 8px !important;
}

.desc-viewer-dialog {
  max-width: calc(100vw - 32px);
}

.desc-viewer-dialog .el-dialog {
  transform: translateY(-20px);
  margin-bottom: 0;
  max-height: calc(100vh - 24px);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.desc-viewer-dialog .el-dialog__body {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  padding-top: 8px;
  padding-bottom: 12px;
}

.desc-viewer-dialog .desc-viewer {
  display: flex;
  flex-direction: column;
  max-height: 100%;
}
</style>
