<template>
  <div>
    <el-card shadow="never">
      <template #header>导出任务数据</template>
      <el-form :inline="true" :model="taskFilters">
        <el-form-item label="状态">
          <el-select
            v-model="taskFilters.status"
            multiple
            collapse-tags
            collapse-tags-tooltip
            clearable
            placeholder="全部"
            style="width: 180px"
          >
            <el-option v-for="s in statusOptions" :key="s" :label="s" :value="s" />
          </el-select>
        </el-form-item>
        <el-form-item label="平台">
          <el-select
            v-model="taskFilters.platform"
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
        <el-form-item label="操作员">
          <el-select
            v-model="taskFilters.assigneeIds"
            multiple
            collapse-tags
            collapse-tags-tooltip
            filterable
            clearable
            placeholder="全部"
            style="width: 180px"
            :loading="operatorLoading"
          >
            <el-option
              v-for="o in operatorOptions"
              :key="o.id"
              :label="o.username"
              :value="o.id"
            />
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
          <el-select
            v-model="approvedFilters.platform"
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
import { onMounted, reactive, ref } from 'vue'
import { downloadApprovedExport, downloadTasksExport } from '@/api/export'
import { listUsersApi } from '@/api/users'

const statusOptions = ['未分发', '待处理', '待审核', '已驳回', '已通过']
const platformOptions = ['淘宝', '京东', '消费者洞察淘宝', '消费者洞察京东']

/** 任务导出筛选：状态/平台/操作员均为多选数组 */
const taskFilters = reactive({ status: [], platform: [], assigneeIds: [], keyword: '' })
/** 正式库导出筛选：平台多选 */
const approvedFilters = reactive({ platform: [], keyword: '' })

const exportingTasks = ref(false)
const exportingApproved = ref(false)

/** 启用中的操作员选项（role=operator 且 is_active） */
const operatorOptions = ref([])
const operatorLoading = ref(false)

/** 加载启用操作员，供任务导出筛选使用 */
async function loadOperatorOptions() {
  operatorLoading.value = true
  try {
    const res = await listUsersApi()
    operatorOptions.value = (res.data || [])
      .filter((u) => u.role === 'operator' && u.is_active)
      .map((u) => ({ id: u.id, username: u.username }))
  } finally {
    operatorLoading.value = false
  }
}

async function handleExportTasks() {
  exportingTasks.value = true
  try {
    await downloadTasksExport({
      status: taskFilters.status.length ? taskFilters.status.join(',') : undefined,
      platform: taskFilters.platform.length ? taskFilters.platform.join(',') : undefined,
      assignee_id: taskFilters.assigneeIds.length ? taskFilters.assigneeIds.join(',') : undefined,
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
      platform: approvedFilters.platform.length ? approvedFilters.platform.join(',') : undefined,
      keyword: approvedFilters.keyword || undefined,
    })
  } finally {
    exportingApproved.value = false
  }
}

onMounted(() => {
  loadOperatorOptions()
})
</script>
