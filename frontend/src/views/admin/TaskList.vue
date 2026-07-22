<template>
  <div>
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>任务管理</span>
          <div>
            <el-button
              type="primary"
              :disabled="!selectedIds.length"
              @click="showAssignDialog = true"
            >
              批量分配 ({{ selectedIds.length }})
            </el-button>
            <el-button
              :disabled="!selectedIds.length"
              @click="handleWithdraw"
            >
              撤回待审核
            </el-button>
          </div>
        </div>
      </template>

      <el-form :inline="true" :model="filters" class="filter-form">
        <el-form-item label="状态">
          <el-select v-model="filters.status" clearable placeholder="全部" style="width: 130px">
            <el-option v-for="s in statusOptions" :key="s" :label="s" :value="s" />
          </el-select>
        </el-form-item>
        <el-form-item label="平台">
          <el-select v-model="filters.platform" clearable placeholder="全部" style="width: 160px">
            <el-option v-for="p in platformOptions" :key="p" :label="p" :value="p" />
          </el-select>
        </el-form-item>
        <el-form-item label="关键词">
          <el-input v-model="filters.keyword" placeholder="宝贝ID/名称" clearable style="width: 180px" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadTasks">查询</el-button>
        </el-form-item>
      </el-form>

      <el-table
        :data="tableData"
        v-loading="loading"
        border
        stripe
        @selection-change="onSelectionChange"
      >
        <el-table-column type="selection" width="50" />
        <el-table-column prop="row_no" label="序号" width="70" />
        <el-table-column prop="product_id" label="宝贝ID" width="140" />
        <el-table-column prop="product_name" label="宝贝名称" min-width="180" show-overflow-tooltip />
        <el-table-column prop="platform" label="数据平台" width="130" />
        <el-table-column prop="assignee_name" label="操作员" width="100">
          <template #default="{ row }">{{ row.assignee_name || '-' }}</template>
        </el-table-column>
        <el-table-column prop="category_large" label="大类" width="100" />
        <el-table-column prop="status" label="状态" width="90" />
      </el-table>

      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        style="margin-top: 16px; justify-content: flex-end"
        @current-change="loadTasks"
      />
    </el-card>

    <el-dialog v-model="showAssignDialog" title="批量分配" width="400px">
      <el-form label-width="80px">
        <el-form-item label="操作员">
          <el-select v-model="assigneeId" placeholder="请选择操作员" style="width: 100%">
            <el-option
              v-for="u in operators"
              :key="u.id"
              :label="u.username"
              :value="u.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAssignDialog = false">取消</el-button>
        <el-button type="primary" :loading="assigning" @click="handleAssign">确认分配</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { assignTasksApi, listTasksApi, withdrawTasksApi } from '@/api/tasks'
import { listUsersApi } from '@/api/users'

const loading = ref(false)
const assigning = ref(false)
const tableData = ref([])
const selectedIds = ref([])
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)
const showAssignDialog = ref(false)
const assigneeId = ref(null)
const operators = ref([])

const statusOptions = ['未分发', '待处理', '待审核', '已驳回', '已通过']
const platformOptions = ['淘宝', '京东', '消费者洞察淘宝', '消费者洞察京东']

const filters = reactive({ status: '', platform: '', keyword: '' })

function onSelectionChange(rows) {
  selectedIds.value = rows.map((r) => r.id)
}

async function loadTasks() {
  loading.value = true
  try {
    const res = await listTasksApi({
      page: page.value,
      page_size: pageSize.value,
      status: filters.status || undefined,
      platform: filters.platform || undefined,
      keyword: filters.keyword || undefined,
    })
    tableData.value = res.data.items || []
    total.value = res.data.total || 0
  } finally {
    loading.value = false
  }
}

async function loadOperators() {
  const res = await listUsersApi()
  operators.value = (res.data || []).filter((u) => u.role === 'operator' && u.is_active)
}

async function handleAssign() {
  if (!assigneeId.value) {
    ElMessage.warning('请选择操作员')
    return
  }
  assigning.value = true
  try {
    const res = await assignTasksApi(selectedIds.value, assigneeId.value)
    ElMessage.success(res.message)
    showAssignDialog.value = false
    await loadTasks()
  } finally {
    assigning.value = false
  }
}

async function handleWithdraw() {
  const res = await withdrawTasksApi(selectedIds.value)
  ElMessage.success(res.message)
  await loadTasks()
}

onMounted(() => {
  loadTasks()
  loadOperators()
})
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
</style>
