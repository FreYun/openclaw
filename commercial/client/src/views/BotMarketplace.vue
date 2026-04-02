<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../store/auth.js'
import api from '../api/index.js'
import { ElMessage } from 'element-plus'

const router = useRouter()
const auth = useAuthStore()
const bots = ref([])
const loading = ref(true)

onMounted(async () => {
  try {
    const { data } = await api.get('/bots')
    bots.value = data
  } catch (err) {
    ElMessage.error('加载 Bot 列表失败')
  } finally {
    loading.value = false
  }
})

function handleOrder(botId) {
  if (!auth.isLoggedIn) {
    ElMessage.warning('请先登录')
    router.push({ name: 'Login', query: { redirect: `/order/create/${botId}` } })
    return
  }
  router.push(`/order/create/${botId}`)
}
</script>

<template>
  <div>
    <div style="text-align: center; margin-bottom: 30px">
      <h1 style="font-size: 28px; margin: 0 0 8px">找达人</h1>
      <p style="color: #999; margin: 0">选择一位达人为您创作内容</p>
    </div>

    <div v-loading="loading" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px; max-width: 1200px; margin: 0 auto">
      <el-card v-for="bot in bots" :key="bot.bot_id" shadow="hover" style="cursor: pointer" @click="handleOrder(bot.bot_id)">
        <div style="display: flex; align-items: center; gap: 16px; margin-bottom: 12px">
          <el-avatar :size="64" :src="bot.avatar_path ? `/api/bots/${bot.bot_id}/avatar` : undefined">
            {{ bot.display_name[0] }}
          </el-avatar>
          <div>
            <div style="font-size: 18px; font-weight: bold">{{ bot.display_name }}</div>
            <div style="color: #999; font-size: 13px">{{ bot.bot_id }}</div>
          </div>
        </div>
        <p style="color: #666; font-size: 14px; line-height: 1.6; margin: 0 0 12px; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden">
          {{ bot.description || '暂无介绍' }}
        </p>
        <div style="display: flex; gap: 6px; flex-wrap: wrap">
          <el-tag v-for="tag in bot.specialties.slice(0, 4)" :key="tag" size="small" type="info">
            {{ tag }}
          </el-tag>
        </div>
        <div style="margin-top: 16px; text-align: right">
          <el-button type="primary" size="small" @click.stop="handleOrder(bot.bot_id)">下单</el-button>
        </div>
      </el-card>
    </div>

    <el-empty v-if="!loading && bots.length === 0" description="暂无可接单的达人" />
  </div>
</template>
