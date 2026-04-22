import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/login', name: 'Login', component: () => import('../views/Login.vue') },
  { path: '/', name: 'Consult', component: () => import('../views/ConsultPage.vue'), meta: { requiresAuth: true } },
  { path: '/marketplace', name: 'BotMarketplace', component: () => import('../views/BotMarketplace.vue'), meta: { requiresAuth: true } },
  { path: '/order/select-service/:botId', name: 'ServiceSelect', component: () => import('../views/ServiceSelect.vue'), meta: { requiresAuth: true } },
  { path: '/order/create/:botId', name: 'OrderCreate', component: () => import('../views/OrderCreate.vue'), meta: { requiresAuth: true } },
  { path: '/orders', name: 'OrderList', component: () => import('../views/OrderList.vue'), meta: { requiresAuth: true } },
  { path: '/orders/:id', name: 'OrderDetail', component: () => import('../views/OrderDetail.vue'), meta: { requiresAuth: true } },
  { path: '/admin/clients', name: 'AdminClients', component: () => import('../views/AdminClients.vue'), meta: { requiresAuth: true, requiresAdmin: true } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to) => {
  if (to.meta.requiresAuth && !localStorage.getItem('token')) {
    return { name: 'Login', query: { redirect: to.fullPath } }
  }
  if (to.meta.requiresAdmin) {
    const { useAuthStore } = await import('../store/auth.js')
    const auth = useAuthStore()
    if (!auth.client && auth.token) {
      await auth.fetchMe()
    }
    if (auth.client?.role !== 'admin') {
      return { name: 'Consult' }
    }
  }
})

export default router
