import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { public: true },
  },
  {
    path: '/admin',
    component: () => import('@/views/admin/Layout.vue'),
    meta: { role: 'admin' },
    children: [
      {
        path: '',
        redirect: '/admin/imports',
      },
      {
        path: 'imports',
        name: 'AdminImports',
        component: () => import('@/views/admin/ImportList.vue'),
      },
      {
        path: 'rules',
        name: 'AdminRules',
        component: () => import('@/views/admin/RuleManage.vue'),
      },
      {
        path: 'tasks',
        name: 'AdminTasks',
        component: () => import('@/views/admin/TaskList.vue'),
      },
      {
        path: 'reviews',
        name: 'AdminReviews',
        component: () => import('@/views/admin/ReviewList.vue'),
      },
      {
        path: 'approved',
        name: 'AdminApproved',
        component: () => import('@/views/admin/ApprovedList.vue'),
      },
      {
        path: 'export',
        name: 'AdminExport',
        component: () => import('@/views/admin/ExportPage.vue'),
      },
      {
        path: 'users',
        name: 'AdminUsers',
        component: () => import('@/views/admin/UserManage.vue'),
      },
      {
        path: 'logs',
        name: 'AdminLogs',
        component: () => import('@/views/admin/LogList.vue'),
      },
      {
        path: 'settings',
        name: 'AdminSettings',
        component: () => import('@/views/admin/SettingsPage.vue'),
      },
    ],
  },
  {
    path: '/operator',
    component: () => import('@/views/operator/Layout.vue'),
    meta: { role: 'operator' },
    children: [
      {
        path: '',
        redirect: '/operator/tasks',
      },
      {
        path: 'tasks',
        name: 'OperatorTasks',
        component: () => import('@/views/operator/MyTasks.vue'),
      },
    ],
  },
  {
    path: '/',
    redirect: '/login',
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  const userStore = useUserStore()

  if (to.meta.public) {
    if (userStore.isLoggedIn) {
      next(userStore.isAdmin ? '/admin' : '/operator')
    } else {
      next()
    }
    return
  }

  if (!userStore.isLoggedIn) {
    next('/login')
    return
  }

  if (to.meta.role && userStore.user?.role !== to.meta.role) {
    next(userStore.isAdmin ? '/admin' : '/operator')
    return
  }

  next()
})

export default router
