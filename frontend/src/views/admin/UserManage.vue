<template>
  <div>
    <el-card shadow="never">
      <template #header>用户管理</template>

      <el-button type="primary" style="margin-bottom: 16px" @click="openCreate">
        新建用户
      </el-button>

      <el-table :data="users" v-loading="loading" border>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="username" label="账号" width="140" />
        <el-table-column prop="role" label="角色" width="100">
          <template #default="{ row }">
            {{ row.role === 'admin' ? '管理员' : '操作员' }}
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'">
              {{ row.is_active ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" min-width="170" />
        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-button link type="primary" @click="openResetPwd(row)">重置密码</el-button>
            <el-button
              link
              :type="row.is_active ? 'danger' : 'success'"
              @click="toggleActive(row)"
            >
              {{ row.is_active ? '停用' : '启用' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="showCreate" title="新建用户" width="400px">
      <el-form :model="createForm" label-width="80px">
        <el-form-item label="账号">
          <el-input v-model="createForm.username" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="createForm.password" type="password" show-password />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="createForm.role" style="width: 100%">
            <el-option label="操作员" value="operator" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleCreate">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showPwd" title="重置密码" width="400px">
      <el-input v-model="newPassword" type="password" show-password placeholder="新密码" />
      <template #footer>
        <el-button @click="showPwd = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleResetPwd">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { createUserApi, listUsersApi, updateUserApi } from '@/api/users'

const loading = ref(false)
const saving = ref(false)
const users = ref([])
const showCreate = ref(false)
const showPwd = ref(false)
const currentUser = ref(null)
const newPassword = ref('')

const createForm = reactive({
  username: '',
  password: '',
  role: 'operator',
})

async function loadUsers() {
  loading.value = true
  try {
    const res = await listUsersApi()
    users.value = res.data || []
  } finally {
    loading.value = false
  }
}

function openCreate() {
  createForm.username = ''
  createForm.password = ''
  createForm.role = 'operator'
  showCreate.value = true
}

async function handleCreate() {
  if (!createForm.username || !createForm.password) {
    ElMessage.warning('请填写账号和密码')
    return
  }
  saving.value = true
  try {
    await createUserApi({ ...createForm })
    ElMessage.success('创建成功')
    showCreate.value = false
    await loadUsers()
  } finally {
    saving.value = false
  }
}

function openResetPwd(row) {
  currentUser.value = row
  newPassword.value = ''
  showPwd.value = true
}

async function handleResetPwd() {
  if (!newPassword.value) {
    ElMessage.warning('请输入新密码')
    return
  }
  saving.value = true
  try {
    await updateUserApi(currentUser.value.id, { password: newPassword.value })
    ElMessage.success('密码已重置')
    showPwd.value = false
  } finally {
    saving.value = false
  }
}

async function toggleActive(row) {
  await updateUserApi(row.id, { is_active: !row.is_active })
  ElMessage.success('状态已更新')
  await loadUsers()
}

onMounted(loadUsers)
</script>
