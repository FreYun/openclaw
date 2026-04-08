<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../api/index.js'
import { ElMessage, ElMessageBox } from 'element-plus'

const route = useRoute()
const router = useRouter()
const orderId = route.params.id
const order = ref(null)
const loading = ref(true)
const generating = ref(false)
const publishing = ref(false)
const generatingCover = ref(false)
const scheduleDialogVisible = ref(false)
const reviseDialogVisible = ref(false)
const coverDialogVisible = ref(false)
const revisionNote = ref('')
const scheduleTime = ref('')
const coverDescription = ref('')
const materialPreviewUrls = ref({})
let previewRequestId = 0
let pollTimer = null

const statusMap = {
  pending: { label: '待生成', type: 'info' },
  awaiting_review: { label: '待研究部审批', type: 'warning' },
  generating: { label: '生成中', type: 'warning' },
  draft_ready: { label: '待审核', type: '' },
  revision_requested: { label: '修改中', type: 'warning' },
  approved: { label: '已批准', type: 'success' },
  scheduled: { label: '已排期', type: 'success' },
  publishing: { label: '发布中', type: 'warning' },
  published: { label: '已发布', type: 'success' },
  cancelled: { label: '已取消', type: 'info' },
  rejected: { label: '已拒绝', type: 'danger' },
  failed: { label: '失败', type: 'danger' },
}

const requestStatusMap = {
  pending_review: '待研究部审批',
  approved: '已审批，待开始生成',
  generating: '生成中',
  completed: '已完成',
  rejected: '已驳回',
  failed: '生成失败',
}

const latestDraft = computed(() => {
  if (!order.value?.drafts?.length) return null
  return order.value.drafts[0]
})

const latestGenerationRequest = computed(() => order.value?.latest_generation_request || null)
const canGenerate = computed(() => ['pending', 'revision_requested'].includes(order.value?.status))
const canReview = computed(() => order.value?.status === 'draft_ready' && latestDraft.value?.status === 'ready')
const canPublish = computed(() => ['approved', 'scheduled'].includes(order.value?.status))
const canCancel = computed(() => ['pending', 'awaiting_review', 'draft_ready', 'revision_requested', 'approved'].includes(order.value?.status))

const canGenerateCover = computed(() => {
  const blocked = ['cancelled', 'rejected', 'published', 'publishing']
  return order.value && !blocked.includes(order.value.status)
})

const imageCount = computed(() => {
  return order.value?.materials?.filter((m) => m.file_type.startsWith('image/')).length || 0
})

const previewMaterials = computed(() => {
  return (order.value?.materials || []).filter(
    (m) => m.file_type.startsWith('image/') && materialPreviewUrls.value[m.id]
  )
})

const previewSrcList = computed(() => {
  return previewMaterials.value.map((m) => materialPreviewUrls.value[m.id])
})

function shouldPollStatus(status) {
  return ['awaiting_review', 'generating'].includes(status)
}

function formatDate(value) {
  if (!value) return '-'
  return new Date(value.endsWith('Z') ? value : `${value}Z`).toLocaleString('zh-CN')
}

function getPreviewIndex(materialId) {
  return previewMaterials.value.findIndex((m) => m.id === materialId)
}

function revokePreviewUrls(urls = materialPreviewUrls.value) {
  Object.values(urls).forEach((url) => {
    if (url) URL.revokeObjectURL(url)
  })
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

async function loadMaterialPreviews(materials) {
  const requestId = ++previewRequestId
  const imageMaterials = materials?.filter((m) => m.file_type.startsWith('image/')) || []

  if (imageMaterials.length === 0) {
    revokePreviewUrls()
    materialPreviewUrls.value = {}
    return
  }

  const nextUrls = {}
  await Promise.all(imageMaterials.map(async (material) => {
    try {
      const { data } = await api.get(`/orders/${orderId}/materials/${material.id}/download`, {
        responseType: 'blob',
      })
      nextUrls[material.id] = URL.createObjectURL(data)
    } catch {}
  }))

  if (requestId !== previewRequestId) {
    revokePreviewUrls(nextUrls)
    return
  }

  revokePreviewUrls()
  materialPreviewUrls.value = nextUrls
}

async function fetchOrder({ silent = false } = {}) {
  if (!silent) loading.value = true
  try {
    const { data } = await api.get(`/orders/${orderId}`)
    order.value = data
    await loadMaterialPreviews(data.materials)

    if (shouldPollStatus(data.status)) {
      startPolling()
    } else {
      stopPolling()
    }
  } catch (err) {
    ElMessage.error('加载订单失败')
    stopPolling()
    router.push('/orders')
  } finally {
    if (!silent) loading.value = false
  }
}

function startPolling() {
  if (pollTimer) return

  pollTimer = setInterval(async () => {
    await fetchOrder({ silent: true })
    if (!shouldPollStatus(order.value?.status)) {
      stopPolling()
      if (order.value?.status === 'draft_ready') {
        ElMessage.success('草稿已生成，请审核')
      }
    }
  }, 5000)
}

onMounted(() => {
  fetchOrder()
})

onUnmounted(() => {
  previewRequestId += 1
  stopPolling()
  revokePreviewUrls()
})

async function handleGenerate() {
  generating.value = true
  try {
    await api.post(`/orders/${orderId}/generate`)
    ElMessage.success('草稿申请已提交，等待研究部审批')
    await fetchOrder()
  } catch (err) {
    ElMessage.error(err.response?.data?.error || '提交失败')
  } finally {
    generating.value = false
  }
}

async function handleApprove() {
  try {
    await ElMessageBox.confirm('确认批准此草稿？', '批准确认')
    await api.post(`/orders/${orderId}/drafts/${latestDraft.value.version}/approve`)
    ElMessage.success('草稿已批准')
    await fetchOrder()
  } catch (err) {
    if (err !== 'cancel') ElMessage.error(err.response?.data?.error || '操作失败')
  }
}

async function handleRevise() {
  if (!revisionNote.value.trim()) {
    return ElMessage.warning('请填写修改意见')
  }
  try {
    await api.post(`/orders/${orderId}/drafts/${latestDraft.value.version}/revise`, {
      revision_note: revisionNote.value,
    })
    ElMessage.success('修改意见已提交')
    reviseDialogVisible.value = false
    revisionNote.value = ''
    await fetchOrder()
  } catch (err) {
    ElMessage.error(err.response?.data?.error || '操作失败')
  }
}

async function handleSchedule() {
  if (!scheduleTime.value) return ElMessage.warning('请选择发布时间')
  try {
    await api.post(`/orders/${orderId}/schedule`, { schedule_at: new Date(scheduleTime.value).toISOString() })
    ElMessage.success('发布时间已设置')
    scheduleDialogVisible.value = false
    await fetchOrder()
  } catch (err) {
    ElMessage.error(err.response?.data?.error || '设置失败')
  }
}

async function handlePublish() {
  try {
    await ElMessageBox.confirm('确认提交发布？', '发布确认')
    publishing.value = true
    await api.post(`/orders/${orderId}/publish`)
    ElMessage.success('已提交到发布队列')
    await fetchOrder()
  } catch (err) {
    if (err !== 'cancel') ElMessage.error(err.response?.data?.error || '发布失败')
  } finally {
    publishing.value = false
  }
}

async function handleCancel() {
  try {
    await ElMessageBox.confirm('确认取消此订单？', '取消确认', { type: 'warning' })
    await api.post(`/orders/${orderId}/cancel`)
    ElMessage.success('订单已取消')
    await fetchOrder()
  } catch (err) {
    if (err !== 'cancel') ElMessage.error(err.response?.data?.error || '操作失败')
  }
}

async function handleGenerateCover() {
  if (!coverDescription.value.trim()) {
    return ElMessage.warning('请描述封面内容')
  }
  generatingCover.value = true
  try {
    const { data } = await api.post(`/orders/${orderId}/generate-cover`, {
      description: coverDescription.value,
    })
    ElMessage.success(`封面已生成 (${data.files?.length || 0} 张)`)
    coverDialogVisible.value = false
    coverDescription.value = ''
    await fetchOrder()
  } catch (err) {
    ElMessage.error(err.response?.data?.error || '封面生成失败')
  } finally {
    generatingCover.value = false
  }
}
</script>

<template>
  <div v-loading="loading" style="max-width: 900px; margin: 0 auto">
    <el-page-header @back="router.push('/orders')" title="返回订单列表">
      <template #content>订单详情</template>
    </el-page-header>

    <template v-if="order">
      <el-card style="margin: 20px 0">
        <div style="display: flex; justify-content: space-between; align-items: start">
          <div>
            <h3 style="margin: 0 0 8px">{{ order.title || '(未命名订单)' }}</h3>
            <div style="color: #999; font-size: 13px; margin-bottom: 4px">
              达人：{{ order.bot_name || order.bot_id }} · {{ { text_to_image: '图文卡片', image: '图文', longform: '长文' }[order.content_type] }}
            </div>
            <div style="color: #999; font-size: 13px">
              创建时间：{{ formatDate(order.created_at) }}
            </div>
          </div>
          <el-tag :type="statusMap[order.status]?.type || 'info'" size="large">
            {{ statusMap[order.status]?.label || order.status }}
          </el-tag>
        </div>
      </el-card>

      <el-card style="margin-bottom: 20px">
        <template #header><span style="font-weight: bold">内容要求</span></template>
        <pre style="white-space: pre-wrap; word-break: break-word; margin: 0; font-family: inherit; line-height: 1.6">{{ order.requirements }}</pre>
        <div v-if="order.reference_links?.length" style="margin-top: 12px">
          <div style="color: #999; font-size: 13px; margin-bottom: 4px">参考链接：</div>
          <div v-for="link in order.reference_links" :key="link">
            <a :href="link" target="_blank" style="color: #409eff; font-size: 13px">{{ link }}</a>
          </div>
        </div>
      </el-card>

      <el-card v-if="order.materials?.length" style="margin-bottom: 20px">
        <template #header>
          <div style="display: flex; justify-content: space-between; align-items: center">
            <span style="font-weight: bold">素材 ({{ order.materials.length }}{{ imageCount > 0 ? `，含 ${imageCount} 张图` : '' }})</span>
            <el-button v-if="canGenerateCover" size="small" type="warning" @click="coverDialogVisible = true">
              生成封面
            </el-button>
          </div>
        </template>
        <div style="display: flex; gap: 12px; flex-wrap: wrap">
          <div v-for="m in order.materials" :key="m.id" style="text-align: center">
            <div v-if="m.file_type.startsWith('image/')" style="width: 100px; height: 100px; border-radius: 8px; overflow: hidden; border: 1px solid #eee">
              <el-image
                v-if="materialPreviewUrls[m.id]"
                :src="materialPreviewUrls[m.id]"
                :preview-src-list="previewSrcList"
                :initial-index="getPreviewIndex(m.id)"
                fit="cover"
                preview-teleported
                style="width: 100%; height: 100%; cursor: zoom-in"
              />
              <div v-else style="width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; background: #f5f7fa; color: #999; font-size: 12px">
                加载失败
              </div>
            </div>
            <div v-else style="width: 100px; height: 100px; border-radius: 8px; border: 1px solid #eee; display: flex; align-items: center; justify-content: center; background: #f5f7fa; padding: 4px">
              <span style="font-size: 11px; color: #999; word-break: break-all">{{ m.file_name }}</span>
            </div>
          </div>
        </div>
      </el-card>

      <el-card v-else-if="canGenerateCover" style="margin-bottom: 20px">
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span style="color: #999">暂无素材</span>
          <el-button size="small" type="warning" @click="coverDialogVisible = true">
            生成封面
          </el-button>
        </div>
      </el-card>

      <el-card style="margin-bottom: 20px">
        <template #header>
          <div style="display: flex; justify-content: space-between; align-items: center">
            <span style="font-weight: bold">草稿</span>
            <el-button v-if="canGenerate" type="primary" size="small" :loading="generating" @click="handleGenerate">
              {{ order.drafts?.length ? '提交重生成审批' : '提交草稿审批' }}
            </el-button>
          </div>
        </template>

        <div v-if="latestGenerationRequest" style="margin-bottom: 16px; padding: 12px 14px; border-radius: 8px; background: #f7f8fa; border: 1px solid #ebeef5">
          <div style="font-size: 13px; color: #606266; margin-bottom: 4px">
            最新审批单：V{{ latestGenerationRequest.version }} · {{ requestStatusMap[latestGenerationRequest.status] || latestGenerationRequest.status }}
          </div>
          <div style="font-size: 12px; color: #909399">
            提交时间：{{ formatDate(latestGenerationRequest.created_at) }}
          </div>
          <div v-if="latestGenerationRequest.reviewer_note" style="font-size: 12px; color: #e6a23c; margin-top: 6px">
            研究部备注：{{ latestGenerationRequest.reviewer_note }}
          </div>
        </div>

        <div v-if="order.status === 'awaiting_review'" style="text-align: center; padding: 36px 20px">
          <div style="color: #e6a23c; font-size: 18px; margin-bottom: 8px">审批中</div>
          <div style="color: #999">草稿申请已提交，等待研究部审批后开始生成</div>
        </div>

        <div v-else-if="order.status === 'generating'" style="text-align: center; padding: 40px">
          <div style="color: #409eff; font-size: 20px; margin-bottom: 8px">...</div>
          <div style="color: #999">正在生成草稿，请稍候...</div>
        </div>

        <template v-else-if="latestDraft && latestDraft.status !== 'pending'">
          <el-tabs v-if="order.drafts.length > 1" type="border-card">
            <el-tab-pane v-for="draft in order.drafts" :key="draft.version" :label="`V${draft.version}`">
              <div style="margin-bottom: 12px">
                <span style="font-weight: bold; font-size: 16px">{{ draft.title }}</span>
                <el-tag :type="draft.status === 'approved' ? 'success' : draft.status === 'revision_requested' ? 'warning' : 'info'" size="small" style="margin-left: 8px">
                  {{ { ready: '待审核', approved: '已通过', revision_requested: '已修改', superseded: '已替换', pending: '生成中', failed: '失败' }[draft.status] || draft.status }}
                </el-tag>
              </div>
              <div v-if="draft.card_text" style="background: #f5f7fa; padding: 16px; border-radius: 8px; margin-bottom: 12px">
                <div style="font-size: 12px; color: #999; margin-bottom: 4px">卡片文字</div>
                <pre style="white-space: pre-wrap; margin: 0; font-family: inherit">{{ draft.card_text }}</pre>
              </div>
              <pre style="white-space: pre-wrap; word-break: break-word; margin: 0; font-family: inherit; line-height: 1.8">{{ draft.content }}</pre>
              <div v-if="draft.tags?.length" style="margin-top: 12px; display: flex; gap: 6px">
                <el-tag v-for="tag in draft.tags" :key="tag" size="small">#{{ tag }}</el-tag>
              </div>
              <div v-if="draft.revision_note" style="margin-top: 12px; padding: 12px; background: #fff7e6; border-radius: 8px; border: 1px solid #ffe7ba">
                <div style="font-size: 12px; color: #999; margin-bottom: 4px">修改意见</div>
                <div>{{ draft.revision_note }}</div>
              </div>
            </el-tab-pane>
          </el-tabs>

          <template v-else>
            <div style="margin-bottom: 12px">
              <span style="font-weight: bold; font-size: 16px">{{ latestDraft.title }}</span>
            </div>
            <div v-if="latestDraft.card_text" style="background: #f5f7fa; padding: 16px; border-radius: 8px; margin-bottom: 12px">
              <div style="font-size: 12px; color: #999; margin-bottom: 4px">卡片文字</div>
              <pre style="white-space: pre-wrap; margin: 0; font-family: inherit">{{ latestDraft.card_text }}</pre>
            </div>
            <pre style="white-space: pre-wrap; word-break: break-word; margin: 0; font-family: inherit; line-height: 1.8">{{ latestDraft.content }}</pre>
            <div v-if="latestDraft.tags?.length" style="margin-top: 12px; display: flex; gap: 6px">
              <el-tag v-for="tag in latestDraft.tags" :key="tag" size="small">#{{ tag }}</el-tag>
            </div>
          </template>
        </template>

        <el-empty v-else description="暂无草稿" />
      </el-card>

      <el-card v-if="canReview || canPublish || canCancel">
        <div style="display: flex; gap: 12px; flex-wrap: wrap">
          <template v-if="canReview">
            <el-button type="success" @click="handleApprove">通过</el-button>
            <el-button type="warning" @click="reviseDialogVisible = true">修改意见</el-button>
          </template>
          <template v-if="canPublish">
            <el-button type="primary" @click="scheduleDialogVisible = true">安排发布</el-button>
            <el-button type="success" :loading="publishing" @click="handlePublish">立即发布</el-button>
          </template>
          <el-button v-if="canCancel" type="danger" plain @click="handleCancel">取消订单</el-button>
        </div>
      </el-card>

      <div v-if="order.schedule_at" style="margin-top: 12px; color: #999; text-align: center">
        计划发布时间：{{ formatDate(order.schedule_at) }}
      </div>
    </template>

    <el-dialog v-model="reviseDialogVisible" title="修改意见" width="500px">
      <el-input v-model="revisionNote" type="textarea" :rows="4" placeholder="请详细描述您希望修改的内容..." maxlength="500" show-word-limit />
      <template #footer>
        <el-button @click="reviseDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleRevise">提交</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="scheduleDialogVisible" title="安排发布时间" width="400px">
      <el-date-picker v-model="scheduleTime" type="datetime" placeholder="选择发布时间" style="width: 100%" :disabled-date="(d) => d < new Date()" />
      <template #footer>
        <el-button @click="scheduleDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSchedule">确认</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="coverDialogVisible" title="生成封面" width="500px">
      <p style="color: #666; margin: 0 0 12px">系统会使用该达人的专属画风生成封面图片</p>
      <el-input
        v-model="coverDescription"
        type="textarea"
        :rows="4"
        placeholder="描述封面内容，例如：一只橙色小猫咪站在金币堆上，背景是上涨的K线图，配文'黄金起飞！'"
        maxlength="500"
        show-word-limit
      />
      <template #footer>
        <el-button @click="coverDialogVisible = false">取消</el-button>
        <el-button type="warning" :loading="generatingCover" @click="handleGenerateCover">
          {{ generatingCover ? '生成中...' : '生成封面' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>
