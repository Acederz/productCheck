<template>
  <div>
    <el-card shadow="never">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="操作日志" name="operations">
          <el-form :inline="true" style="margin-bottom: 12px">
            <el-form-item label="操作类型">
              <el-select
                v-model="opAction"
                clearable
                filterable
                placeholder="全部"
                style="width: 200px"
              >
                <el-option
                  v-for="opt in actionOptions"
                  :key="opt.value"
                  :label="opt.label"
                  :value="opt.value"
                />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleSearchOps">查询</el-button>
              <el-button @click="handleResetOps">重置</el-button>
            </el-form-item>
          </el-form>

          <el-table :data="opLogs" v-loading="opLoading" border stripe>
            <el-table-column prop="id" label="编号" width="70" />
            <el-table-column prop="username" label="操作人" width="100" />
            <el-table-column prop="action_label" label="操作" width="130" />
            <el-table-column prop="target_type_label" label="对象类型" width="110" />
            <el-table-column label="对象编号" width="100">
              <template #default="{ row }">
                {{ row.target_id != null ? row.target_id : '-' }}
              </template>
            </el-table-column>
            <el-table-column label="详情" min-width="280" show-overflow-tooltip>
              <template #default="{ row }">
                {{ row.detail_text || '-' }}
              </template>
            </el-table-column>
            <el-table-column prop="ip" label="IP" width="120" />
            <el-table-column prop="created_at" label="时间" width="170" />
          </el-table>

          <el-pagination
            v-model:current-page="opPage"
            v-model:page-size="opPageSize"
            :total="opTotal"
            :page-sizes="[10, 20, 50]"
            layout="total, sizes, prev, pager, next"
            style="margin-top: 12px; justify-content: flex-end"
            @current-change="loadOperations"
            @size-change="handleOpSizeChange"
          />
        </el-tab-pane>

        <el-tab-pane label="字段变更" name="changes">
          <el-form :inline="true" style="margin-bottom: 12px">
            <el-form-item label="任务编号">
              <el-input v-model="changeTaskId" clearable style="width: 140px" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleSearchChanges">查询</el-button>
              <el-button @click="handleResetChanges">重置</el-button>
            </el-form-item>
          </el-form>

          <el-table :data="changeLogs" v-loading="changeLoading" border stripe>
            <el-table-column prop="task_id" label="任务编号" width="100" />
            <el-table-column prop="field_label" label="字段" width="110" />
            <el-table-column prop="old_value" label="修改前" min-width="140" show-overflow-tooltip>
              <template #default="{ row }">{{ row.old_value || '空' }}</template>
            </el-table-column>
            <el-table-column prop="new_value" label="修改后" min-width="140" show-overflow-tooltip>
              <template #default="{ row }">{{ row.new_value || '空' }}</template>
            </el-table-column>
            <el-table-column prop="reason" label="原因" width="140" show-overflow-tooltip>
              <template #default="{ row }">{{ row.reason || '-' }}</template>
            </el-table-column>
            <el-table-column prop="username" label="操作人" width="100" />
            <el-table-column prop="created_at" label="时间" width="170" />
          </el-table>

          <el-pagination
            v-model:current-page="changePage"
            v-model:page-size="changePageSize"
            :total="changeTotal"
            :page-sizes="[10, 20, 50]"
            layout="total, sizes, prev, pager, next"
            style="margin-top: 12px; justify-content: flex-end"
            @current-change="loadChanges"
            @size-change="handleChangeSizeChange"
          />
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { listFieldChangeLogsApi, listOperationLogsApi } from '@/api/logs'

const activeTab = ref('operations')
const opLoading = ref(false)
const changeLoading = ref(false)
const opLogs = ref([])
const changeLogs = ref([])
const opPage = ref(1)
const opPageSize = ref(20)
const opTotal = ref(0)
const changePage = ref(1)
const changePageSize = ref(20)
const changeTotal = ref(0)
const opAction = ref('')
const changeTaskId = ref('')
const actionOptions = ref([])

async function loadOperations() {
  opLoading.value = true
  try {
    const res = await listOperationLogsApi({
      page: opPage.value,
      page_size: opPageSize.value,
      action: opAction.value || undefined,
    })
    opLogs.value = res.data.items || []
    opTotal.value = res.data.total || 0
    if (res.data.action_options?.length) {
      actionOptions.value = res.data.action_options
    }
  } finally {
    opLoading.value = false
  }
}

async function loadChanges() {
  changeLoading.value = true
  try {
    const res = await listFieldChangeLogsApi({
      page: changePage.value,
      page_size: changePageSize.value,
      task_id: changeTaskId.value || undefined,
    })
    changeLogs.value = res.data.items || []
    changeTotal.value = res.data.total || 0
  } finally {
    changeLoading.value = false
  }
}

function handleSearchOps() {
  opPage.value = 1
  loadOperations()
}

function handleResetOps() {
  opAction.value = ''
  opPage.value = 1
  loadOperations()
}

function handleOpSizeChange() {
  opPage.value = 1
  loadOperations()
}

function handleSearchChanges() {
  changePage.value = 1
  loadChanges()
}

function handleResetChanges() {
  changeTaskId.value = ''
  changePage.value = 1
  loadChanges()
}

function handleChangeSizeChange() {
  changePage.value = 1
  loadChanges()
}

onMounted(() => {
  loadOperations()
  loadChanges()
})
</script>
