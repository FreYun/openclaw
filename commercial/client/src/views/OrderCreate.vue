<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../api/index.js'
import { useConsultStore } from '../store/consult.js'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()
const consultStore = useConsultStore()
const botId = route.params.botId
const skillId = route.query.skill || null
const bot = ref(null)
const selectedSkill = ref(null)
const loading = ref(false)
const contentType = ref('text_to_image')
const requirementsInput = ref('')

onMounted(async () => {
  if (consultStore.result) {
    const cr = consultStore.result
    if (cr.content_type) contentType.value = cr.content_type
    const parts = []
    if (cr.guidance) parts.push(`【运营指导】\n${cr.guidance}`)
    if (consultStore.originalMessage) parts.push(`【客户需求】\n${consultStore.originalMessage}`)
    if (parts.length) requirementsInput.value = parts.join('\n\n')
    consultStore.clear()
  }
  try {
    const { data } = await api.get(`/bots/${botId}`)
    bot.value = data
  } catch {
    ElMessage.error('Bot 不存在')
    router.push('/')
    return
  }
  if (skillId) {
    try {
      const { data } = await api.get(`/bots/${botId}/offerings`)
      const found = data.offerings?.find(o => o.id === skillId)
      if (found) {
        selectedSkill.value = found
        if (found.content_type) contentType.value = found.content_type
      }
    } catch {}
  }
})

async function handleSubmit() {
  const skill = selectedSkill.value
  if (skill?.requirements_placeholder && !requirementsInput.value.trim()) {
    ElMessage.warning('请填写必要的素材信息')
    return
  }
  loading.value = true
  try {
    const payload = {
      bot_id: botId,
      content_type: contentType.value,
    }
    if (skillId) payload.skill_id = skillId
    if (requirementsInput.value.trim()) {
      const prefix = skill?.requirements_prefix || ''
      payload.requirements = prefix + requirementsInput.value.trim()
    }
    const { data: order } = await api.post('/orders', payload)
    const query = (skillId && requirementsInput.value.trim()) ? { autostart: '1' } : {}
    router.push({ path: `/orders/${order.id}`, query })
  } catch (err) {
    ElMessage.error(err.response?.data?.error || '创建失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div style="max-width: 700px; margin: 0 auto">
    <el-page-header @back="router.go(-1)" title="返回">
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

    <!-- Selected service tag -->
    <el-alert
      v-if="selectedSkill"
      :title="`${selectedSkill.icon} ${selectedSkill.name}`"
      :description="selectedSkill.description"
      type="info"
      :closable="false"
      show-icon
      style="margin-bottom: 16px"
    />

    <el-card>
      <el-form label-position="top" @submit.prevent="handleSubmit">
        <el-form-item v-if="!selectedSkill?.content_type" label="内容类型">
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

        <!-- Skill-specific requirements input -->
        <el-form-item
          v-if="selectedSkill?.requirements_placeholder"
          :label="selectedSkill.requirements_label || '内容要求'"
          required
        >
          <el-input
            v-model="requirementsInput"
            type="textarea"
            :placeholder="selectedSkill.requirements_placeholder"
            :autosize="{ minRows: 6, maxRows: 20 }"
          />
        </el-form-item>

        <div v-if="!selectedSkill?.requirements_placeholder" style="font-size: 13px; color: #909399; line-height: 1.6; margin: 8px 0 16px; padding: 12px; background: #f5f7fa; border-radius: 6px">
          创建后进入订单详情页,可以继续填写标题、内容要求、上传素材(DOCX 会自动解析文字进内容要求),然后点「向 bot 提需求」开始生成草稿。
        </div>

        <el-form-item>
          <el-button type="primary" native-type="submit" :loading="loading" size="large" style="width: 100%">
            {{ selectedSkill && requirementsInput.trim() ? '创建订单并开始生成' : '创建订单并进入详情页' }}
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>
