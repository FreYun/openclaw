import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/login', name: 'Login', component: () => import('../views/Login.vue') },
  { path: '/', name: 'BotMarketplace', component: () => import('../views/BotMarketplace.vue') },
  { path: '/order/create/:botId', name: 'OrderCreate', component: () => import('../views/OrderCreate.vue'), meta: { requiresAuth: true } },
  { path: '/orders', name: 'OrderList', component: () => import('../views/OrderList.vue'), meta: { requiresAuth: true } },
  { path: '/orders/:id', name: 'OrderDetail', component: () => import('../views/OrderDetail.vue'), meta: { requiresAuth: true } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  if (to.meta.requiresAuth && !localStorage.getItem('token')) {
    return { name: 'Login', query: { redirect: to.fullPath } }
  }
})

export default router
