<template>
  <div>
    <el-card shadow="never">
      <template #header>导出任务数据</template>
      <el-form :inline="true" :model="taskFilters">
        <el-form-item label="状态">
          <el-select v-model="taskFilters.status" clearable style="width: 130px">
            <el-option v-for="s in statusOptions" :key="s" :label="s" :value="s" />
          </el-select>
        </el-form-item>
        <el-form-item label="平台">
          <el-select v-model="taskFilters.platform" clearable style="width: 160px">
            <el-option v-for="p in platformOptions" :key="p" :label="p" :value="p" />
          </el-select>
        </el-form-item>
        <el-form-item label="关键词">
          <el-input v-model="taskFilters.keyword" clearable style="width: 160px" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="exportingTasks" @click="handleExportTasks">
            导出 Excel
          </el-button>
        </el-form-item>
      </el-form>
      <el-text type="info" size="small">
        包含 19 个业务字段 + 状态、操作员、审核人、驳回原因、各时间字段
      </el-text>
    </el-card>

    <el-card shadow="never" style="margin-top: 16px">
      <template #header>导出正式库数据</template>
      <el-form :inline="true" :model="approvedFilters">
        <el-form-item label="平台">
          <el-select v-model="approvedFilters.platform" clearable style="width: 160px">
            <el-option v-for="p in platformOptions" :key="p" :label="p" :value="p" />
          </el-select>
        </el-form-item>
        <el-form-item label="关键词">
          <el-input v-model="approvedFilters.keyword" clearable style="width: 160px" />
        </el-form-item>
        <el-form-item>
          <el-button type="success" :loading="exportingApproved" @click="handleExportApproved">
            导出正式库
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { downloadApprovedExport, downloadTasksExport } from '@/api/export'

const statusOptions = ['未分发', '待处理', '待审核', '已驳回', '已通过']
const platformOptions = ['淘宝', '京东', '消费者洞察淘宝', '消费者洞察京东']

const taskFilters = reactive({ status: '', platform: '', keyword: '' })
const approvedFilters = reactive({ platform: '', keyword: '' })
const exportingTasks = ref(false)
const exportingApproved = ref(false)

async function handleExportTasks() {
  exportingTasks.value = true
  try {
    await downloadTasksExport({
      status: taskFilters.status || undefined,
      platform: taskFilters.platform || undefined,
      keyword: taskFilters.keyword || undefined,
    })
  } finally {
    exportingTasks.value = false
  }
}

async function handleExportApproved() {
  exportingApproved.value = true
  try {
    await downloadApprovedExport({
      platform: approvedFilters.platform || undefined,
      keyword: approvedFilters.keyword || undefined,
    })
  } finally {
    exportingApproved.value = false
  }
}
</script>
