<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../api/index.js'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()
const botId = route.params.botId
const bot = ref(null)
const offerings = ref([])
const loading = ref(true)

onMounted(async () => {
  try {
    const [botRes, offeringsRes] = await Promise.all([
      api.get(`/bots/${botId}`),
      api.get(`/bots/${botId}/offerings`),
    ])
    bot.value = botRes.data
    offerings.value = offeringsRes.data.offerings || []
    if (offerings.value.length === 0) {
      router.replace(`/order/create/${botId}`)
    }
  } catch {
    ElMessage.error('加载失败')
    router.push('/marketplace')
  } finally {
    loading.value = false
  }
})

function selectService(offering) {
  router.push(`/order/create/${botId}?skill=${offering.id}`)
}
</script>

<template>
  <div class="service-select-page">
    <el-page-header @back="router.go(-1)" title="返回">
      <template #content>选择服务</template>
    </el-page-header>

    <div v-if="bot" class="bot-header">
      <el-avatar :size="56" :src="`/api/bots/${botId}/avatar`">{{ bot.display_name?.[0] }}</el-avatar>
      <div class="bot-header__info">
        <div class="bot-header__name">{{ bot.display_name }}</div>
        <div class="bot-header__desc">{{ bot.style_summary || bot.description?.slice(0, 60) }}</div>
      </div>
    </div>

    <div v-loading="loading" class="offerings-grid">
      <div
        v-for="offering in offerings"
        :key="offering.id"
        class="offering-card"
        @click="selectService(offering)"
      >
        <div class="offering-card__icon">{{ offering.icon }}</div>
        <div class="offering-card__body">
          <div class="offering-card__name">{{ offering.name }}</div>
          <div class="offering-card__desc">{{ offering.description }}</div>
        </div>
        <div class="offering-card__arrow">
          <el-icon><ArrowRight /></el-icon>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ArrowRight } from '@element-plus/icons-vue'
export default { components: { ArrowRight } }
</script>

<style scoped>
.service-select-page {
  max-width: 700px;
  margin: 0 auto;
  padding: 20px;
}

.bot-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin: 24px 0;
  padding: 20px;
  background: #f5f7fa;
  border-radius: 12px;
}

.bot-header__name {
  font-weight: bold;
  font-size: 18px;
}

.bot-header__desc {
  color: #909399;
  font-size: 13px;
  margin-top: 4px;
}

.offerings-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.offering-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.offering-card:hover {
  border-color: #409eff;
  box-shadow: 0 2px 12px rgba(64, 158, 255, 0.15);
  transform: translateY(-1px);
}

.offering-card__icon {
  font-size: 32px;
  flex-shrink: 0;
  width: 48px;
  text-align: center;
}

.offering-card__body {
  flex: 1;
  min-width: 0;
}

.offering-card__name {
  font-weight: 600;
  font-size: 16px;
  margin-bottom: 4px;
}

.offering-card__desc {
  color: #909399;
  font-size: 13px;
  line-height: 1.5;
}

.offering-card__arrow {
  flex-shrink: 0;
  color: #c0c4cc;
  font-size: 16px;
}
</style>
