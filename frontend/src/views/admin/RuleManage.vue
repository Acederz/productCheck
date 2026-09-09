<template>
  <div class="rule-manage">
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

    <el-card shadow="never" class="skip-card">
      <template #header>
        <div class="card-header">
          <span>无需填写字段规则</span>
          <el-tag v-if="skipVersion" type="success">当前版本：{{ skipVersion.version_no }}</el-tag>
          <el-tag v-else type="warning">尚未导入规则</el-tag>
        </div>
      </template>

      <el-alert
        title="请上传「无需填写字段.xlsx」。每次导入全量覆盖上一版；仅按「大类」生效，「区隔」列不参与判断。"
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
        :on-change="handleSkipFileChange"
      >
        <el-button>选择 Excel（必选）</el-button>
      </el-upload>

      <el-input
        v-model="skipRemark"
        placeholder="备注（可选）"
        style="max-width: 400px; margin: 12px 0"
      />

      <el-button type="primary" :loading="skipImporting" @click="handleSkipImport">
        导入无需填写字段规则
      </el-button>

      <el-descriptions v-if="skipLastResult" :column="2" border style="margin-top: 20px">
        <el-descriptions-item label="版本号">{{ skipLastResult.version_no }}</el-descriptions-item>
        <el-descriptions-item label="规则条数">{{ skipLastResult.rule_count }}</el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getRuleVersionApi, importRulesApi } from '@/api/rules'
import { getSkipFieldRuleVersionApi, importSkipFieldRulesApi } from '@/api/skipFieldRules'

const version = ref(null)
const selectedFile = ref(null)
const remark = ref('')
const importing = ref(false)
const lastResult = ref(null)

const skipVersion = ref(null)
const skipSelectedFile = ref(null)
const skipRemark = ref('')
const skipImporting = ref(false)
const skipLastResult = ref(null)

function handleFileChange(file) {
  selectedFile.value = file.raw
}

function handleSkipFileChange(file) {
  skipSelectedFile.value = file.raw
}

async function loadVersion() {
  const res = await getRuleVersionApi()
  version.value = res.data
}

async function loadSkipVersion() {
  const res = await getSkipFieldRuleVersionApi()
  skipVersion.value = res.data
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

async function handleSkipImport() {
  if (!skipSelectedFile.value) {
    ElMessage.warning('请先选择 Excel 文件')
    return
  }
  skipImporting.value = true
  try {
    const res = await importSkipFieldRulesApi(skipSelectedFile.value, skipRemark.value)
    skipLastResult.value = res.data
    ElMessage.success(res.message || '无需填写字段规则导入成功')
    skipSelectedFile.value = null
    await loadSkipVersion()
  } finally {
    skipImporting.value = false
  }
}

onMounted(() => {
  loadVersion()
  loadSkipVersion()
})
</script>

<style scoped>
.rule-manage {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.skip-card {
  margin-top: 0;
}
</style>
