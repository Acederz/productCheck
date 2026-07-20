<template>
  <el-container class="layout">
    <el-aside width="220px" class="aside">
      <div class="logo">分类管理平台</div>
      <el-menu :default-active="activeMenu" router background-color="#001529" text-color="#fff" active-text-color="#409eff">
        <el-menu-item index="/admin/imports">数据导入</el-menu-item>
        <el-menu-item index="/admin/rules">分类规则</el-menu-item>
        <el-menu-item index="/admin/tasks">任务管理</el-menu-item>
        <el-menu-item index="/admin/reviews">审核中心</el-menu-item>
        <el-menu-item index="/admin/approved">正式数据</el-menu-item>
        <el-menu-item index="/admin/export">数据导出</el-menu-item>
        <el-menu-item index="/admin/users">用户管理</el-menu-item>
        <el-menu-item index="/admin/logs">操作日志</el-menu-item>
        <el-menu-item index="/admin/settings">系统设置</el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="header">
        <span>管理员：{{ userStore.user?.username }}</span>
        <el-button link type="danger" @click="handleLogout">退出</el-button>
      </el-header>
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const activeMenu = computed(() => route.path)

async function handleLogout() {
  await userStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.layout {
  min-height: 100vh;
}

.aside {
  background: #001529;
  color: #fff;
}

.logo {
  height: 60px;
  line-height: 60px;
  text-align: center;
  font-weight: 600;
  color: #fff;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid #ebeef5;
}
</style>
