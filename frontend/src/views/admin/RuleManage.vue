<template>
  <div>
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>分类规则管理</span>
          <el-tag v-if="version" type="success">当前版本：{{ version.version_no }}</el-tag>
          <el-tag v-else type="warning">尚未导入规则</el-tag>
        </div>
      </template>

      <el-alert
        title="首次使用请先导入「分类规则全维度拆分_最新版.xlsx」。不上传文件时，将使用项目内样例文件。"
        type="info"
        :closable="false"
        show-icon
        style="margin-bottom: 16px"
      />

      <el-upload
        :auto-upload="false"
        :show-file-list="true"
        :limit="1"
        accept=".xlsx"
        :on-change="handleFileChange"
      >
        <el-button>选择规则 Excel（可选）</el-button>
      </el-upload>

      <el-input
        v-model="remark"
        placeholder="备注（可选）"
        style="max-width: 400px; margin: 12px 0"
      />

      <el-button type="primary" :loading="importing" @click="handleImport">
        导入规则
      </el-button>

      <el-descriptions v-if="lastResult" :column="2" border style="margin-top: 20px">
        <el-descriptions-item label="版本号">{{ lastResult.version_no }}</el-descriptions-item>
        <el-descriptions-item label="主规则行数">{{ lastResult.node_count }}</el-descriptions-item>
        <el-descriptions-item label="补充规则行数">{{ lastResult.field_rule_count }}</el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getRuleVersionApi, importRulesApi } from '@/api/rules'

const version = ref(null)
const selectedFile = ref(null)
const remark = ref('')
const importing = ref(false)
const lastResult = ref(null)

function handleFileChange(file) {
  selectedFile.value = file.raw
}

async function loadVersion() {
  const res = await getRuleVersionApi()
  version.value = res.data
}

async function handleImport() {
  importing.value = true
  try {
    const res = await importRulesApi(selectedFile.value, remark.value)
    lastResult.value = res.data
    ElMessage.success(res.message || '规则导入成功')
    selectedFile.value = null
    await loadVersion()
  } finally {
    importing.value = false
  }
}

onMounted(loadVersion)
</script>

<style scoped>
.card-header {
  display: flex;
  align-items: center;
  gap: 12px;
}
</style>
