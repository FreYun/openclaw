<script setup>
import { useAuthStore } from './store/auth.js'
import { useRouter } from 'vue-router'

const auth = useAuthStore()
const router = useRouter()

auth.fetchMe()

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <el-container style="min-height: 100vh">
    <el-header style="display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #eee; background: #fff">
      <div style="display: flex; align-items: center; gap: 24px">
        <router-link to="/" style="font-size: 20px; font-weight: bold; text-decoration: none; color: #333">
          天天出版社 · 商单系统
        </router-link>
        <router-link v-if="auth.isLoggedIn" to="/marketplace" style="text-decoration: none; color: #666">
          达人列表
        </router-link>
        <router-link v-if="auth.isLoggedIn" to="/orders" style="text-decoration: none; color: #666">
          我的订单
        </router-link>
        <router-link v-if="auth.isAdmin" to="/admin/clients" style="text-decoration: none; color: #e6a23c; font-weight: 500">
          用户管理
        </router-link>
      </div>
      <div>
        <template v-if="auth.isLoggedIn">
          <span style="margin-right: 12px; color: #666">{{ auth.client?.display_name }}</span>
          <el-button text @click="logout">退出</el-button>
        </template>
        <el-button v-else type="primary" @click="router.push('/login')">登录</el-button>
      </div>
    </el-header>
    <el-main style="background: #f5f7fa; padding: 20px">
      <router-view />
    </el-main>
  </el-container>
</template>

<style>
body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
</style>
