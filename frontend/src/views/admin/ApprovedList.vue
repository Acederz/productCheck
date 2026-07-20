<template>
  <div class="approved-page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>正式数据</span>
          <el-button type="success" @click="handleExport">导出 Excel</el-button>
        </div>
      </template>

      <el-form :inline="true" :model="filters" class="filter-form" @submit.prevent>
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
        <el-table :data="tableData" v-loading="loading" border stripe size="small">
          <el-table-column prop="product_id" label="宝贝ID" width="130" fixed="left" />
          <el-table-column
            prop="product_name"
            label="宝贝名称"
            width="160"
            fixed="left"
            show-overflow-tooltip
          />
          <el-table-column prop="platform" label="平台" width="110" />
          <el-table-column prop="brand" label="品牌" width="100" show-overflow-tooltip>
            <template #default="{ row }">{{ row.brand || '-' }}</template>
          </el-table-column>

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

          <el-table-column label="产品属性" width="200">
            <template #default="{ row }">
              <div class="product-attr-cell" :title="formatProductAttr(row.product_attr)">
                {{ formatProductAttr(row.product_attr) }}
              </div>
            </template>
          </el-table-column>

          <el-table-column label="宝贝文描图" width="110">
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

          <el-table-column prop="is_operating" label="是否经营" width="90" />
          <el-table-column label="大类" width="120" show-overflow-tooltip>
            <template #default="{ row }">{{ formatMulti(row.category_large) }}</template>
          </el-table-column>
          <el-table-column label="区隔" width="120" show-overflow-tooltip>
            <template #default="{ row }">{{ formatMulti(row.category_segment) }}</template>
          </el-table-column>
          <el-table-column label="类别" width="120" show-overflow-tooltip>
            <template #default="{ row }">{{ formatMulti(row.category_type) }}</template>
          </el-table-column>
          <el-table-column label="主材质" width="110" show-overflow-tooltip>
            <template #default="{ row }">{{ formatMulti(row.material_main) }}</template>
          </el-table-column>
          <el-table-column label="辅材质" width="110" show-overflow-tooltip>
            <template #default="{ row }">{{ formatMulti(row.material_aux) }}</template>
          </el-table-column>
          <el-table-column label="包装方式" width="110" show-overflow-tooltip>
            <template #default="{ row }">{{ formatMulti(row.packaging) }}</template>
          </el-table-column>
          <el-table-column label="尺寸" width="110" show-overflow-tooltip>
            <template #default="{ row }">{{ formatMulti(row.size) }}</template>
          </el-table-column>
          <el-table-column label="卷数" width="100" show-overflow-tooltip>
            <template #default="{ row }">{{ formatMulti(row.roll_count) }}</template>
          </el-table-column>
          <el-table-column label="总入数" width="100" show-overflow-tooltip>
            <template #default="{ row }">{{ formatMulti(row.total_count) }}</template>
          </el-table-column>

          <el-table-column prop="version" label="版本" width="70" />
          <el-table-column prop="approved_by_name" label="审核人" width="100">
            <template #default="{ row }">{{ row.approved_by_name || '-' }}</template>
          </el-table-column>
          <el-table-column prop="approved_at" label="审核时间" width="170" />
        </el-table>
      </div>

      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        class="table-pagination"
        @current-change="loadList"
        @size-change="handlePageSizeChange"
      />
    </el-card>

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
          :class="{ 'is-draggable': descZoomScale > 1, 'is-dragging': descDragging }"
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
import { listApprovedApi } from '@/api/approved'
import { downloadApprovedExport } from '@/api/export'

const loading = ref(false)
const tableData = ref([])
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const platformOptions = ['淘宝', '京东', '消费者洞察淘宝', '消费者洞察京东']
const filters = reactive({ platform: [], keyword: '' })

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
const descDragStart = { x: 0, y: 0, panX: 0, panY: 0 }

const descImageStyle = computed(() => ({
  transform: `translate(${descPanX.value}px, ${descPanY.value}px) scale(${descZoomScale.value})`,
}))

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

function formatMulti(val) {
  if (val === null || val === undefined || val === '') return '-'
  if (Array.isArray(val)) return val.length ? val.join('，') : '-'
  return String(val)
}

function formatProductAttr(val) {
  if (val === null || val === undefined) return '-'
  if (typeof val === 'string') {
    const s = val.trim()
    return s || '-'
  }
  if (Array.isArray(val)) return val.join('；')
  try {
    return JSON.stringify(val)
  } catch (e) {
    return String(val)
  }
}

function normalizeDescImages(descImages) {
  if (Array.isArray(descImages)) return descImages.filter(Boolean)
  if (typeof descImages === 'string') {
    const raw = descImages.trim()
    if (!raw) return []
    try {
      const parsed = JSON.parse(raw)
      if (Array.isArray(parsed)) return parsed.filter(Boolean)
    } catch (e) {
      /* 非 JSON */
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

function buildQueryParams() {
  return {
    page: page.value,
    page_size: pageSize.value,
    platform: resolveFilterValues(filters.platform, platformOptions),
    keyword: filters.keyword?.trim() || undefined,
  }
}

function handleSearch() {
  page.value = 1
  loadList()
}

function handleReset() {
  filters.platform = []
  filters.keyword = ''
  page.value = 1
  loadList()
}

function handlePageSizeChange() {
  page.value = 1
  loadList()
}

async function loadList() {
  loading.value = true
  try {
    const res = await listApprovedApi(buildQueryParams())
    tableData.value = (res.data.items || []).map((row) => ({
      ...row,
      desc_images: normalizeDescImages(row.desc_images),
    }))
    total.value = res.data.total || 0
  } finally {
    loading.value = false
  }
}

async function handleExport() {
  await downloadApprovedExport({
    platform: resolveFilterValues(filters.platform, platformOptions),
    keyword: filters.keyword?.trim() || undefined,
  })
}

onMounted(loadList)
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
.table-wrap {
  width: 100%;
  overflow-x: auto;
}
.table-pagination {
  margin-top: 16px;
  justify-content: flex-end;
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
