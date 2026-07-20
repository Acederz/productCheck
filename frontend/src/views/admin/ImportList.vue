<template>
  <div>
    <el-card shadow="never" class="upload-card">
      <template #header>上传待分类 Excel</template>
      <el-upload
        :auto-upload="false"
        :show-file-list="true"
        :limit="1"
        accept=".xlsx,.xls"
        :on-change="handleFileChange"
      >
        <el-button type="primary">选择文件</el-button>
        <template #tip>
          <div class="tip">表头须与「分类平台表头.xlsx」一致，支持多平台混合导入</div>
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
        <el-table-column prop="status" label="状态" width="100" />
        <el-table-column prop="created_at" label="导入时间" width="180" />
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button
              v-if="row.has_error_report"
              link
              type="primary"
              @click="downloadErrors(row.id)"
            >
              错误报告
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { listImportsApi, uploadImportApi, downloadImportErrorsApi } from '@/api/imports'
import { useUserStore } from '@/stores/user'

const loading = ref(false)
const uploading = ref(false)
const batches = ref([])
const selectedFile = ref(null)
const userStore = useUserStore()

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
    ElMessage.success(
      `导入完成：成功 ${res.data.success_rows} 条，失败 ${res.data.fail_rows} 条`
    )
    selectedFile.value = null
    await loadBatches()
  } finally {
    uploading.value = false
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
</style>
