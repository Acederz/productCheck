<template>
  <el-container class="layout">
    <el-header class="header">
      <span class="logo">我的分类任务</span>
      <div>
        <span class="username">{{ userStore.user?.username }}</span>
        <el-button link type="danger" @click="handleLogout">退出</el-button>
      </div>
    </el-header>
    <el-main>
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

async function handleLogout() {
  await userStore.logout()
  router.push('/login')
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
