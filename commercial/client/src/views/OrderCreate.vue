<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../api/index.js'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()
const botId = route.params.botId
const bot = ref(null)
const loading = ref(false)
const fileList = ref([])

const form = ref({
  title: '',
  requirements: '',
  content_type: 'text_to_image',
  reference_links: [''],
})

// Image upload only available in 'image' mode
const showImageUpload = computed(() => form.value.content_type === 'image')
// DOCX + text always allowed
const acceptTypes = computed(() => {
  if (form.value.content_type === 'image') {
    return 'image/jpeg,image/png,image/webp,.docx,text/plain'
  }
  return '.docx,text/plain'
})

onMounted(async () => {
  try {
    const { data } = await api.get(`/bots/${botId}`)
    bot.value = data
  } catch {
    ElMessage.error('Bot 不存在')
    router.push('/')
  }
})

function addLink() {
  form.value.reference_links.push('')
}

function removeLink(idx) {
  form.value.reference_links.splice(idx, 1)
}

// Clear image files when switching away from image mode
function onContentTypeChange(val) {
  if (val !== 'image') {
    fileList.value = fileList.value.filter((f) => !f.raw?.type?.startsWith('image/'))
  }
}

async function handleSubmit() {
  if (!form.value.requirements.trim()) {
    return ElMessage.warning('请填写内容要求')
  }

  loading.value = true
  try {
    const links = form.value.reference_links.filter((l) => l.trim())
    const { data: order } = await api.post('/orders', {
      bot_id: botId,
      title: form.value.title,
      requirements: form.value.requirements,
      content_type: form.value.content_type,
      reference_links: links,
    })

    // Upload materials if any
    if (fileList.value.length > 0) {
      const formData = new FormData()
      for (const file of fileList.value) {
        formData.append('files', file.raw)
      }
      const { data: uploadResult } = await api.post(`/orders/${order.id}/materials`, formData)

      // If DOCX with images auto-switched to image mode, notify user
      if (uploadResult.mode_changed) {
        ElMessage.info('检测到 DOCX 中包含图片，已自动切换为图文模式')
      }
    }

    ElMessage.success('订单创建成功')
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

    <!-- Order form -->
    <el-card>
      <el-form label-position="top" @submit.prevent="handleSubmit">
        <el-form-item label="订单标题（选填）">
          <el-input v-model="form.title" placeholder="给订单起个名字，方便管理" maxlength="50" show-word-limit />
        </el-form-item>

        <el-form-item label="内容要求" required>
          <el-input v-model="form.requirements" type="textarea" :rows="6" placeholder="请详细描述您希望达人创作的内容，包括主题、风格、目标受众等" maxlength="2000" show-word-limit />
        </el-form-item>

        <el-form-item label="内容类型">
          <el-radio-group v-model="form.content_type" @change="onContentTypeChange">
            <el-radio value="text_to_image">
              <span>图文卡片</span>
              <span style="font-size: 12px; color: #999; margin-left: 4px">文字自动生成卡片图</span>
            </el-radio>
            <el-radio value="image">
              <span>图文</span>
              <span style="font-size: 12px; color: #999; margin-left: 4px">上传配图 + 文案</span>
            </el-radio>
            <el-radio value="longform">长文</el-radio>
          </el-radio-group>
        </el-form-item>

        <!-- Image upload: only in image mode -->
        <el-form-item v-if="showImageUpload" label="上传配图">
          <el-upload
            v-model:file-list="fileList"
            :auto-upload="false"
            multiple
            :limit="10"
            :accept="acceptTypes"
            drag
          >
            <div style="padding: 20px">
              <div style="font-size: 14px; color: #999">将配图拖拽到此处，或点击上传</div>
              <div style="font-size: 12px; color: #ccc; margin-top: 4px">支持 jpg/png/webp/docx/txt，单文件不超过 10MB，最多 10 个</div>
            </div>
          </el-upload>
        </el-form-item>

        <!-- DOCX/text upload: always available but without images -->
        <el-form-item v-if="!showImageUpload" label="上传素材（选填）">
          <el-upload
            v-model:file-list="fileList"
            :auto-upload="false"
            multiple
            :limit="10"
            :accept="acceptTypes"
            drag
          >
            <div style="padding: 20px">
              <div style="font-size: 14px; color: #999">上传 DOCX 或文本文件</div>
              <div style="font-size: 12px; color: #ccc; margin-top: 4px">支持 docx/txt。DOCX 中包含图片会自动切换为图文模式</div>
            </div>
          </el-upload>
        </el-form-item>

        <el-form-item label="参考链接（选填）">
          <div v-for="(link, idx) in form.reference_links" :key="idx" style="display: flex; gap: 8px; margin-bottom: 8px; width: 100%">
            <el-input v-model="form.reference_links[idx]" placeholder="https://..." />
            <el-button v-if="form.reference_links.length > 1" text type="danger" @click="removeLink(idx)">删除</el-button>
          </div>
          <el-button text type="primary" @click="addLink">+ 添加链接</el-button>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" native-type="submit" :loading="loading" size="large" style="width: 100%">
            提交订单
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>
