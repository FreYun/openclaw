<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../api/index.js'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()
const botId = route.params.botId
const bot = ref(null)
const loading = ref(false)
const contentType = ref('text_to_image')

onMounted(async () => {
  try {
    const { data } = await api.get(`/bots/${botId}`)
    bot.value = data
  } catch {
    ElMessage.error('Bot 不存在')
    router.push('/')
  }
})

async function handleSubmit() {
  loading.value = true
  try {
    const { data: order } = await api.post('/orders', {
      bot_id: botId,
      content_type: contentType.value,
    })
    router.push(`/orders/${order.id}`)
  } catch (err) {
    ElMessage.error(err.response?.data?.error || '创建失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div style="max-width: 700px; margin: 0 auto">
    <el-page-header @back="router.push('/')" title="返回">
      <template #content>创建订单</template>
    </el-page-header>

    <!-- Bot info -->
    <el-card v-if="bot" style="margin: 20px 0">
      <div style="display: flex; align-items: center; gap: 16px">
        <el-avatar :size="48" :src="`/api/bots/${botId}/avatar`">{{ bot.display_name[0] }}</el-avatar>
        <div>
          <div style="font-weight: bold; font-size: 16px">{{ bot.display_name }}</div>
          <div style="color: #999; font-size: 13px">{{ bot.style_summary || bot.description?.slice(0, 60) }}</div>
        </div>
      </div>
    </el-card>

    <el-card>
      <el-form label-position="top" @submit.prevent="handleSubmit">
        <el-form-item label="内容类型">
          <el-radio-group v-model="contentType">
            <el-radio value="text_to_image">
              <span>文字生图</span>
              <span style="font-size: 12px; color: #999; margin-left: 4px">文字自动生成卡片图</span>
            </el-radio>
            <el-radio value="image">
              <span>图文</span>
              <span style="font-size: 12px; color: #999; margin-left: 4px">上传配图 + 文案</span>
            </el-radio>
            <el-radio value="longform">长文</el-radio>
          </el-radio-group>
        </el-form-item>

        <div style="font-size: 13px; color: #909399; line-height: 1.6; margin: 8px 0 16px; padding: 12px; background: #f5f7fa; border-radius: 6px">
          💡 创建后进入订单详情页,可以继续填写标题、内容要求、上传素材(DOCX 会自动解析文字进内容要求),然后点「向 bot 提需求」开始生成草稿。
        </div>

        <el-form-item>
          <el-button type="primary" native-type="submit" :loading="loading" size="large" style="width: 100%">
            创建订单并进入详情页
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>
