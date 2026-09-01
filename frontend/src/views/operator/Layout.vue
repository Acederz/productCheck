<template>
  <el-container class="layout">
    <el-header class="header">
      <span class="logo">我的分类任务</span>
      <div>
        <span class="username">{{ userStore.user?.username }}</span>
        <el-button link type="primary" @click="openChangePwd">修改密码</el-button>
        <el-button link type="danger" @click="handleLogout">退出</el-button>
      </div>
    </el-header>
    <el-main>
      <router-view />
    </el-main>

    <el-dialog
      v-model="changePwdVisible"
      title="修改密码"
      width="420px"
      :close-on-click-modal="false"
      @closed="resetChangePwdForm"
    >
      <el-form label-width="100px">
        <el-form-item label="原密码">
          <el-input
            v-model="changePwdForm.old_password"
            type="password"
            show-password
            autocomplete="off"
          />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input
            v-model="changePwdForm.new_password"
            type="password"
            show-password
            autocomplete="new-password"
          />
        </el-form-item>
        <el-form-item label="确认新密码">
          <el-input
            v-model="changePwdForm.confirm_password"
            type="password"
            show-password
            autocomplete="new-password"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="changePwdVisible = false">取消</el-button>
        <el-button type="primary" :loading="changePwdSubmitting" @click="submitChangePwd">
          确定
        </el-button>
      </template>
    </el-dialog>
  </el-container>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { changePasswordApi } from '@/api/auth'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

const changePwdVisible = ref(false)
const changePwdSubmitting = ref(false)
const changePwdForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: '',
})

/** 新密码强度：至少 8 位且同时含字母与数字 */
function passwordStrengthOk(pwd) {
  if (!pwd || pwd.length < 8) return false
  return /[A-Za-z]/.test(pwd) && /\d/.test(pwd)
}

function openChangePwd() {
  changePwdVisible.value = true
}

function resetChangePwdForm() {
  changePwdForm.old_password = ''
  changePwdForm.new_password = ''
  changePwdForm.confirm_password = ''
}

async function handleLogout() {
  await userStore.logout()
  router.push('/login')
}

async function submitChangePwd() {
  const { old_password, new_password, confirm_password } = changePwdForm

  if (!old_password || !new_password || !confirm_password) {
    ElMessage.warning('请填写完整')
    return
  }
  if (new_password !== confirm_password) {
    ElMessage.warning('两次输入的新密码不一致')
    return
  }
  if (!passwordStrengthOk(new_password)) {
    ElMessage.warning('新密码至少 8 位，且需同时包含字母和数字')
    return
  }

  changePwdSubmitting.value = true
  try {
    const res = await changePasswordApi({ old_password, new_password, confirm_password })
    ElMessage.success(res.message || '密码修改成功')
    changePwdVisible.value = false
    resetChangePwdForm()
  } catch {
    // 错误由 request 拦截器统一提示
  } finally {
    changePwdSubmitting.value = false
  }
}
</script>

<style scoped>
.layout {
  min-height: 100vh;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid #ebeef5;
}

.logo {
  font-weight: 600;
  color: #303133;
}

.username {
  margin-right: 12px;
  color: #606266;
}

.layout :deep(.el-main) {
  padding: 12px;
  background: #f5f7fa;
}
</style>
