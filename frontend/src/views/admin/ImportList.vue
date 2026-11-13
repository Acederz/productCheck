<template>
  <div>
    <el-card shadow="never" class="upload-card">
      <template #header>上传待分类 Excel</template>
      <el-upload
        ref="uploadRef"
        :auto-upload="false"
        :show-file-list="true"
        :limit="1"
        accept=".xlsx,.xls"
        :on-change="handleFileChange"
      >
        <el-button type="primary">选择文件</el-button>
        <template #tip>
          <div class="tip">
            表头须与「分类平台表头.xlsx」一致（19 列）；可在末尾加「操作员」列，填登录用户名即可导入时自动分配；留空则仍由管理员分配。
          </div>
        </template>
      </el-upload>
      <el-button
        type="success"
        class="upload-btn"
        :loading="uploading"
        :disabled="!selectedFile"
        @click="handleUpload"
      >
        开始导入
      </el-button>
    </el-card>

    <el-card shadow="never" style="margin-top: 16px">
      <template #header>导入记录</template>
      <el-table :data="batches" v-loading="loading" style="width: 100%">
        <el-table-column prop="batch_no" label="批次号" width="180" />
        <el-table-column prop="file_name" label="文件名" min-width="180" />
        <el-table-column prop="total_rows" label="总行数" width="90" />
        <el-table-column prop="success_rows" label="成功" width="80" />
        <el-table-column prop="fail_rows" label="失败" width="80" />
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tooltip
              v-if="row.fail_reason"
              :content="row.fail_reason"
              placement="top"
            >
              <el-tag :type="statusMeta(row).type" effect="light">
                {{ statusMeta(row).label }}
              </el-tag>
            </el-tooltip>
            <el-tag v-else :type="statusMeta(row).type" effect="light">
              {{ statusMeta(row).label }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="导入时间" width="180" />
        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-button
              v-if="row.has_error_report"
              link
              type="primary"
              @click="downloadErrors(row.id)"
            >
              错误报告
            </el-button>
            <el-button link type="danger" @click="handleDelete(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog
      v-model="resultVisible"
      title="导入结果"
      width="560px"
      :close-on-click-modal="false"
    >
      <el-result
        class="import-result"
        :icon="resultView.icon"
        :title="resultView.title"
        :sub-title="resultView.subTitle"
      >
        <template v-if="importResult.batch" #extra>
          <el-descriptions :column="2" border size="small" class="result-desc">
            <el-descriptions-item label="批次号" :span="2">
              {{ importResult.batch.batch_no }}
            </el-descriptions-item>
            <el-descriptions-item label="文件名" :span="2">
              {{ importResult.batch.file_name }}
            </el-descriptions-item>
            <template v-if="importResult.kind !== 'failed'">
              <el-descriptions-item label="总行数">
                {{ importResult.batch.total_rows }}
              </el-descriptions-item>
              <el-descriptions-item label="成功">
                {{ importResult.batch.success_rows }}
              </el-descriptions-item>
              <el-descriptions-item label="失败">
                {{ importResult.batch.fail_rows }}
              </el-descriptions-item>
              <el-descriptions-item label="提醒">
                {{ importResult.batch.warning_rows ?? 0 }}
              </el-descriptions-item>
              <el-descriptions-item label="自动分配">
                {{ importResult.batch.assigned_rows ?? 0 }}
              </el-descriptions-item>
            </template>
            <el-descriptions-item label="导入时间" :span="importResult.kind === 'failed' ? 2 : 1">
              {{ importResult.batch.created_at }}
            </el-descriptions-item>
          </el-descriptions>
        </template>
      </el-result>
      <template #footer>
        <el-button
          v-if="importResult.batch?.has_error_report"
          type="warning"
          plain
          @click="downloadErrors(importResult.batch.id)"
        >
          下载错误报告
        </el-button>
        <el-button type="primary" @click="resultVisible = false">知道了</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  listImportsApi,
  uploadImportApi,
  downloadImportErrorsApi,
  deleteImportApi,
} from '@/api/imports'
import { useUserStore } from '@/stores/user'

const loading = ref(false)
const uploading = ref(false)
const batches = ref([])
const selectedFile = ref(null)
const uploadRef = ref(null)
const userStore = useUserStore()

/** 导入结果弹框：kind 为 success / partial / failed */
const resultVisible = ref(false)
const importResult = reactive({ kind: 'success', batch: null, message: '' })

const resultView = computed(() => {
  const batch = importResult.batch
  if (importResult.kind === 'failed') {
    return { icon: 'error', title: '导入失败', subTitle: importResult.message }
  }
  if (importResult.kind === 'partial') {
    return {
      icon: 'warning',
      title: '部分导入成功',
      subTitle: `成功 ${batch.success_rows} 行，失败 ${batch.fail_rows} 行，失败明细请下载错误报告`,
    }
  }
  return {
    icon: 'success',
    title: '导入成功',
    subTitle: `共 ${batch.success_rows} 行全部导入`,
  }
})

/** 导入记录状态标签 */
function statusMeta(row) {
  if (row.status === 'failed') return { label: '导入失败', type: 'danger' }
  if (row.status === 'processing') return { label: '导入中', type: 'info' }
  if (row.fail_rows > 0) return { label: '部分失败', type: 'warning' }
  return { label: '导入成功', type: 'success' }
}

/** 从上传异常中提取失败原因与失败批次 */
function parseUploadError(e) {
  // 服务器处理超过 300 秒会被中止并回滚，本次导入不会留下数据
  if (e.code === 'ECONNABORTED' || [502, 504].includes(e.response?.status)) {
    return {
      batch: null,
      message: '服务器处理超时（超过 5 分钟），本次导入未完成，请把文件拆小后重新导入',
    }
  }
  const body = e.response?.data
  return {
    batch: body?.data || null,
    message: body?.message || e.message || '网络错误',
  }
}

function showResult(kind, batch, message = '') {
  importResult.kind = kind
  importResult.batch = batch
  importResult.message = message
  resultVisible.value = true
}

function handleFileChange(file) {
  selectedFile.value = file.raw
}

async function loadBatches() {
  loading.value = true
  try {
    const res = await listImportsApi({ page: 1, page_size: 50 })
    batches.value = res.data.items || []
  } finally {
    loading.value = false
  }
}

async function handleUpload() {
  if (!selectedFile.value) return
  uploading.value = true
  try {
    const res = await uploadImportApi(selectedFile.value)
    const batch = res.data
    showResult(batch.fail_rows > 0 ? 'partial' : 'success', batch)
    selectedFile.value = null
    uploadRef.value?.clearFiles()
  } catch (e) {
    const { batch, message } = parseUploadError(e)
    showResult('failed', batch, message)
  } finally {
    uploading.value = false
    // 成功或失败都会产生批次记录，统一刷新
    loadBatches().catch(() => {})
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(
      `确定删除批次 ${row.batch_no}？将删除该批次下任务及仍归属该批次的正式库数据，且不可恢复。`,
      '删除批次',
      {
        type: 'warning',
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        confirmButtonClass: 'el-button--danger',
      }
    )
    const res = await deleteImportApi(row.id)
    ElMessage.success(
      `已删除任务 ${res.data.deleted_tasks} 条、正式库 ${res.data.deleted_approved} 条`
    )
    await loadBatches()
  } catch (e) {
    // 用户取消或错误提示已由 request 拦截器处理
  }
}

function downloadErrors(batchId) {
  const token = userStore.token
  const url = `${downloadImportErrorsApi(batchId)}?token=${token}`
  // 使用带 Authorization 的方式下载
  fetch(`/api/imports/${batchId}/errors`, {
    headers: { Authorization: `Bearer ${token}` },
  })
    .then((r) => {
      if (!r.ok) throw new Error('下载失败')
      return r.blob()
    })
    .then((blob) => {
      const a = document.createElement('a')
      a.href = URL.createObjectURL(blob)
      a.download = `errors_${batchId}.xlsx`
      a.click()
    })
    .catch(() => ElMessage.error('下载错误报告失败'))
}

onMounted(loadBatches)
</script>

<style scoped>
.upload-card .tip {
  color: #909399;
  font-size: 13px;
  margin-top: 8px;
}
.upload-btn {
  margin-top: 16px;
}
.import-result {
  padding: 8px 0 0;
}
.result-desc {
  width: 460px;
  text-align: left;
}
</style>
