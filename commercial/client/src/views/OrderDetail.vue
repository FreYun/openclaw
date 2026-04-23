<script setup>
import { ref, onMounted, onUnmounted, computed, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../api/index.js'
import { ElMessage, ElMessageBox } from 'element-plus'

const route = useRoute()
const router = useRouter()
const orderId = route.params.id
const order = ref(null)
const loading = ref(true)
const generatingCover = ref(false)
// Tracks the most recent cover-generation attempt so the UI can render progress /
// result in the cover card body (replacing the static intro text).
// state: 'idle' | 'running' | 'success' | 'error'
const coverStatus = ref({ state: 'idle', startedAt: 0, finishedAt: 0, message: '', files: [], error: '' })
// Ticks once a second while generation is running so the elapsed-seconds label
// and the fake-progress bar update without a manual re-render.
const coverNowTick = ref(Date.now())
let coverTickTimer = null
const scheduleDialogVisible = ref(false)
const coverDialogVisible = ref(false)
const coverCount = ref(1)
const submittingPublish = ref(false)
const scheduleTime = ref('')
const coverDescription = ref('')
const refineInput = ref('')
const refineSending = ref(false)
// refineTurns is a client-side in-memory log of (instruction, resulting draft).
// Refresh clears it (by design — the backend truth is the drafts table).
const refineTurns = ref([])
const refineQuota = ref({ used: 0, max: 50 })
// Inline draft editing state — only the latest "ready" draft is editable.
const editingField = ref(null) // 'title' | 'content' | 'card_text' | 'tags'
const editBuffer = ref({ title: '', content: '', card_text: '', tags: '' })
const savingDraft = ref(false)
// Inline order editing state (title / requirements / reference_links / content_type)
const editingOrderField = ref(null)
const orderEditBuffer = ref({ title: '', requirements: '', reference_links: '', content_type: '' })
const savingOrder = ref(false)
const uploadingMaterial = ref(false)
const materialFileInput = ref(null)
// Read-only bot capabilities snapshot (EQUIPPED_SKILLS.md + mcporter.json)
const botCapabilities = ref(null)
const skillDisplayName = ref('')
const materialPreviewUrls = ref({})
let previewRequestId = 0
let pollTimer = null

// Drag-and-drop state for reordering preview images on the draft card.
// dragImageId: the material.id currently being dragged; dragOverImageId: the
// tile currently hovered (used to draw the drop indicator).
const dragImageId = ref(null)
const dragOverImageId = ref(null)
const savingImageOrder = ref(false)

const statusMap = {
  pending: { label: '待生成', type: 'info' },
  awaiting_review: { label: '待研究部审批(旧流程)', type: 'warning' },
  generating: { label: '生成中', type: 'warning' },
  draft_ready: { label: '待审核', type: '' },
  revision_requested: { label: '修改中', type: 'warning' },
  approved: { label: '已批准', type: 'success' },
  scheduled: { label: '已排期', type: 'success' },
  awaiting_publish_review: { label: '待研究部确认发布', type: 'warning' },
  publishing: { label: '发布中', type: 'warning' },
  published: { label: '已发布', type: 'success' },
  cancelled: { label: '已取消', type: 'info' },
  rejected: { label: '已拒绝', type: 'danger' },
  failed: { label: '失败', type: 'danger' },
}

const latestDraft = computed(() => {
  if (!order.value?.drafts?.length) return null
  return order.value.drafts[0]
})
// V1 草稿已出现但 title 还没回填(Qwen 异步生成中)显示"标题生成中"
// V1 草稿都还没生成就用短 id 占位
const isFirstDraftPending = computed(() => {
  if (!order.value) return false
  return Boolean(order.value.drafts?.length) && !order.value.title
})
// Which draft version is currently shown when multiple drafts exist. Snaps
// to the latest whenever a new version is generated.
const selectedDraftVersion = ref(null)
watch(
  () => latestDraft.value?.version,
  (v) => {
    if (v != null && (selectedDraftVersion.value == null || selectedDraftVersion.value < v)) {
      selectedDraftVersion.value = v
    }
  },
  { immediate: true }
)

// New flow: every client turn sends an instruction to the bot and receives
// a fresh draft version. No free chat, no finalize step. The old /generate
// (research approval before generation) path is gone.
const canRefine = computed(() => {
  const blocked = ['awaiting_publish_review', 'publishing', 'published', 'cancelled', 'rejected', 'failed']
  return order.value && !blocked.includes(order.value.status)
})
const canReview = computed(() => order.value?.status === 'draft_ready' && latestDraft.value?.status === 'ready')
const canSubmitPublish = computed(() => ['approved', 'scheduled'].includes(order.value?.status))
const awaitingPublishReview = computed(() => order.value?.status === 'awaiting_publish_review')
const canCancel = computed(() => ['pending', 'awaiting_review', 'draft_ready', 'revision_requested', 'approved', 'awaiting_publish_review'].includes(order.value?.status))
// Whether the client can still edit the order brief (title/requirements/
// materials/reference_links/content_type). Once research is confirming the
// publish or the order is done, everything freezes.
const canEditOrder = computed(() => {
  const editable = ['pending', 'draft_ready', 'revision_requested', 'approved', 'awaiting_review']
  return order.value && editable.includes(order.value.status)
})

// text_to_image mode doesn't need a manual cover — the card image is
// auto-generated from the draft's card_text. Only expose the button for
// `image` / `longform` modes.
const canGenerateCover = computed(() => {
  if (!order.value) return false
  if (order.value.content_type === 'text_to_image') return false
  const blocked = ['cancelled', 'rejected', 'published', 'publishing']
  return !blocked.includes(order.value.status)
})

// Cover thumbnails to display in the success block. Derived from
// coverStatus.files but filtered against order.materials — if the user later
// deletes one of the generated covers from the material area, it disappears
// from the result block too (otherwise we'd show a broken "加载中" tile
// forever because the id no longer exists).
const coverResultFiles = computed(() => {
  const existingIds = new Set((order.value?.materials || []).map((m) => m.id))
  return (coverStatus.value.files || []).filter((f) => !f.id || existingIds.has(f.id))
})

// Elapsed seconds since the cover generation kicked off. Recomputed whenever
// coverNowTick advances (1s cadence while running).
const coverElapsed = computed(() => {
  if (!coverStatus.value.startedAt) return 0
  return Math.max(0, Math.round((coverNowTick.value - coverStatus.value.startedAt) / 1000))
})

// Fake progress: asymptotic curve toward 95% over a typical 90s generation.
// Real progress isn't reported by image-gen MCP, so this is just "show motion
// so the user doesn't think we're stuck" UX sugar. Success jumps it to 100.
const coverProgressPct = computed(() => {
  if (coverStatus.value.state === 'success') return 100
  if (coverStatus.value.state !== 'running') return 0
  const t = coverElapsed.value
  // 0s → 0%, 30s → ~50%, 90s → ~85%, asymptotes at 95%
  return Math.min(95, Math.round(95 * (1 - Math.exp(-t / 45))))
})

watch(
  () => coverStatus.value.state,
  (state) => {
    if (state === 'running') {
      coverNowTick.value = Date.now()
      if (coverTickTimer) clearInterval(coverTickTimer)
      coverTickTimer = setInterval(() => { coverNowTick.value = Date.now() }, 1000)
    } else if (coverTickTimer) {
      clearInterval(coverTickTimer)
      coverTickTimer = null
    }
  }
)

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

function linkifyText(text) {
  if (!text) return ''
  const escaped = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
  return escaped.replace(
    /(https?:\/\/[^\s<>"')\]，。、；]+)/g,
    '<a href="$1" target="_blank" rel="noopener" style="color: #409eff; text-decoration: underline">$1</a>'
  )
}

function shouldPollStatus(status) {
  return ['awaiting_review', 'generating', 'awaiting_publish_review', 'publishing'].includes(status)
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

async function fetchBotCapabilities(botId) {
  if (!botId || botCapabilities.value?.bot_id === botId) return
  try {
    const { data } = await api.get(`/bots/${botId}/capabilities`)
    botCapabilities.value = data
  } catch {
    botCapabilities.value = null
  }
}

// Rebuild the chat turn log from persisted draft rows. Each draft row carries
// the client instruction that produced it (revision_note) and the resulting
// title/version — enough to reconstruct what the chat looked like. Called
// when refineTurns is empty (page reload) so history survives refreshes
// without needing a separate turns table.
function rehydrateRefineTurns(drafts) {
  if (!Array.isArray(drafts) || drafts.length === 0) return
  if (refineTurns.value.length > 0) return
  // Server returns drafts DESC by version; turns render oldest-first.
  const asc = [...drafts].sort((a, b) => a.version - b.version)
  const rebuilt = []
  for (const d of asc) {
    const note = (d.revision_note || '').trim()
    if (!note) continue
    if (d.status === 'failed') {
      rebuilt.push({
        id: `v${d.version}`,
        instruction: note,
        status: 'error',
        draft: null,
        error: '生成失败',
        liveStatusLines: [],
      })
    } else {
      rebuilt.push({
        id: `v${d.version}`,
        instruction: note,
        status: 'success',
        draft: { version: d.version, title: d.title || '' },
        error: null,
        liveStatusLines: [],
      })
    }
  }
  refineTurns.value = rebuilt
}

async function fetchOrder({ silent = false } = {}) {
  if (!silent) loading.value = true
  try {
    const { data } = await api.get(`/orders/${orderId}`)
    order.value = data
    fetchBotCapabilities(data.bot_id)
    if (data.skill_id && !skillDisplayName.value) {
      api.get(`/bots/${data.bot_id}/offerings`).then(({ data: od }) => {
        const found = od.offerings?.find(o => o.id === data.skill_id)
        if (found) skillDisplayName.value = `${found.icon} ${found.name}`
      }).catch(() => {})
    }
    await loadMaterialPreviews(data.materials)
    rehydrateRefineTurns(data.drafts)

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

let titlePollTimer = null
function pollForTitle() {
  if (titlePollTimer) return
  let elapsed = 0
  titlePollTimer = setInterval(async () => {
    elapsed += 20
    await fetchOrder({ silent: true })
    if (order.value?.title || elapsed >= 60) {
      clearInterval(titlePollTimer)
      titlePollTimer = null
    }
  }, 20000)
}

onMounted(async () => {
  await fetchOrder()
  refreshRefineQuota()

  if (route.query.autostart === '1' && order.value?.requirements) {
    refineInput.value = order.value.requirements
    router.replace({ path: route.path, query: {} })
    await nextTick()
    handleRefineSend()
  }
})

onUnmounted(() => {
  previewRequestId += 1
  stopPolling()
  if (titlePollTimer) { clearInterval(titlePollTimer); titlePollTimer = null }
  revokePreviewUrls()
  if (coverTickTimer) { clearInterval(coverTickTimer); coverTickTimer = null }
})

async function handleApprove() {
  try {
    await ElMessageBox.confirm('确认批准此草稿并提交研究部确认发布？', '批准确认')
    await api.post(`/orders/${orderId}/drafts/${latestDraft.value.version}/approve`)
    // Approve 后直接提交研究部，不再需要手动点第二下
    await api.post(`/orders/${orderId}/submit-publish`)
    ElMessage.success('草稿已批准，已提交研究部确认发布')
    await fetchOrder()
  } catch (err) {
    if (err !== 'cancel') ElMessage.error(err.response?.data?.error || '操作失败')
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

async function handleUnapprove() {
  if (!latestDraft.value) return
  try {
    await ElMessageBox.confirm(
      '确认退回到上一步？草稿会回到待审核状态,已安排的发布时间会被清空,你可以继续调整或向 bot 提新需求。',
      '退回确认',
      { type: 'warning' }
    )
    await api.post(`/orders/${orderId}/drafts/${latestDraft.value.version}/unapprove`)
    ElMessage.success('已退回到上一步')
    await fetchOrder()
  } catch (err) {
    if (err !== 'cancel') ElMessage.error(err.response?.data?.error || '操作失败')
  }
}

const refineQuotaExhausted = computed(() => refineQuota.value.used >= refineQuota.value.max)

async function refreshRefineQuota() {
  try {
    const { data } = await api.get(`/orders/${orderId}/refine/quota`)
    if (data?.quota) refineQuota.value = data.quota
  } catch {}
}

// Render a tool_use SSE event as a short single-line status for the chat
// bubble. Keeps UX simple: just "X: 简要参数" — no full transcript.
function formatToolUseStatus(evt) {
  const name = (evt?.tool || '').toLowerCase()
  const preview = evt?.preview || ''
  const map = {
    read: '读取',
    grep: '搜索文件',
    glob: '查找文件',
    websearch: '联网搜索',
    web_search: '联网搜索',
    webfetch: '抓取网页',
    web_fetch: '抓取网页',
    todowrite: '规划任务',
    skill: '调用 skill',
    task: '深度研究',
    bash: '命令行',
  }
  const label = map[name] || evt?.tool || '工具'
  if (preview) {
    const short = preview.length > 50 ? preview.slice(0, 50) + '…' : preview
    return `${label}: ${short}`
  }
  return `${label}...`
}

// Keep full streaming history so user can scroll up; the box CSS caps visible
// height to ~5 lines with overflow-y: auto.
const liveStatusBoxRefs = new Map()
function setLiveStatusBoxRef(id, el) {
  if (el) liveStatusBoxRefs.set(id, el)
  else liveStatusBoxRefs.delete(id)
}

function pushTurnLiveStatus(pendingId, text) {
  const idx = refineTurns.value.findIndex((t) => t.id === pendingId)
  if (idx === -1) return
  const prev = refineTurns.value[idx]
  const lines = Array.isArray(prev.liveStatusLines) ? [...prev.liveStatusLines] : []
  lines.push(text)
  refineTurns.value[idx] = { ...prev, liveStatusLines: lines }
  nextTick(() => {
    const el = liveStatusBoxRefs.get(pendingId)
    if (el) el.scrollTop = el.scrollHeight
  })
}

// Each send = one draft generation turn. Uses SSE streaming:
// POST /refine with Accept: text/event-stream. The server emits `tool_use`
// events while the bot is running plus a terminal `done` or `error` event.
// Browser EventSource does not support POST, so we use fetch + ReadableStream
// and parse SSE manually.
async function handleRefineSend() {
  const text = refineInput.value.trim()
  if (!text) return
  if (refineQuotaExhausted.value) {
    return ElMessage.warning('对话次数已达上限，请联系研究部')
  }

  const pendingId = Date.now()
  refineTurns.value.push({
    id: pendingId,
    instruction: text,
    status: 'pending',
    draft: null,
    error: null,
    liveStatusLines: [],
  })
  refineInput.value = ''
  refineSending.value = true

  try {
    const resp = await fetch(`/api/orders/${orderId}/refine`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
        Authorization: `Bearer ${localStorage.getItem('token') || ''}`,
      },
      body: JSON.stringify({ instruction: text }),
    })

    if (!resp.ok) {
      // Non-2xx — server never opened the stream. Try to read a JSON error body.
      let errMsg = `HTTP ${resp.status}`
      try {
        const body = await resp.json()
        if (body?.error) errMsg = body.error
        if (body?.quota) refineQuota.value = body.quota
      } catch { /* ignore */ }
      throw new Error(errMsg)
    }

    // SSE parser: buffer chunks, split on blank-line event boundaries,
    // parse each block for event name + data payload.
    const reader = resp.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buf = ''
    let finalData = null
    let errorData = null

    const dispatchBlock = (block) => {
      let eventName = 'message'
      let dataLine = ''
      for (const line of block.split('\n')) {
        if (line.startsWith('event:')) eventName = line.slice(6).trim()
        else if (line.startsWith('data:')) dataLine += line.slice(5).trim()
      }
      if (!dataLine) return
      let payload
      try { payload = JSON.parse(dataLine) } catch { return }
      if (eventName === 'tool_use') {
        pushTurnLiveStatus(pendingId, formatToolUseStatus(payload))
      } else if (eventName === 'done') {
        finalData = payload
      } else if (eventName === 'error') {
        errorData = payload
      } else if (eventName === 'start') {
        pushTurnLiveStatus(pendingId, '连接 bot 会话中...')
      }
    }

    // eslint-disable-next-line no-constant-condition
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buf += decoder.decode(value, { stream: true })
      let boundary
      while ((boundary = buf.indexOf('\n\n')) !== -1) {
        const block = buf.slice(0, boundary)
        buf = buf.slice(boundary + 2)
        if (block.trim()) dispatchBlock(block)
      }
    }

    if (errorData) {
      if (errorData.quota) refineQuota.value = errorData.quota
      throw new Error(errorData.error || '生成失败')
    }
    if (!finalData || !finalData.draft) {
      throw new Error('bot 未返回草稿')
    }

    const idx = refineTurns.value.findIndex((t) => t.id === pendingId)
    if (idx !== -1) {
      refineTurns.value[idx] = {
        id: pendingId,
        instruction: text,
        status: 'ready',
        draft: finalData.draft,
        error: null,
        liveStatusLines: [],
      }
    }
    if (finalData.quota) refineQuota.value = finalData.quota
    await fetchOrder({ silent: true })
    // auto-title 是后端异步生成的,首次 fetchOrder 可能还没写入,轮询补取
    if (finalData.draft?.version === 1 && !order.value?.title) {
      pollForTitle()
    }
  } catch (err) {
    const idx = refineTurns.value.findIndex((t) => t.id === pendingId)
    const msg = err.message || '生成失败'
    if (idx !== -1) {
      refineTurns.value[idx] = {
        id: pendingId,
        instruction: text,
        status: 'error',
        draft: null,
        error: msg,
        liveStatusLines: [],
      }
    }
  } finally {
    refineSending.value = false
  }
}

async function handleSubmitPublish() {
  try {
    await ElMessageBox.confirm(
      '将此订单提交研究部进行最终发布确认？提交后将无法再修改草稿。',
      '发布确认'
    )
  } catch {
    return
  }
  submittingPublish.value = true
  try {
    await api.post(`/orders/${orderId}/submit-publish`)
    ElMessage.success('已提交研究部确认发布')
    await fetchOrder()
  } catch (err) {
    ElMessage.error(err.response?.data?.error || '提交失败')
  } finally {
    submittingPublish.value = false
  }
}

// ---------------------------------------------------------------------------
// Inline draft editing — only for the latest "ready" draft.
// ---------------------------------------------------------------------------
const isEditableDraft = computed(
  () => latestDraft.value && latestDraft.value.status === 'ready'
)

function isLatestReady(draft) {
  return draft && latestDraft.value && draft.version === latestDraft.value.version && draft.status === 'ready'
}

function startEdit(field) {
  if (!isEditableDraft.value) return
  const draft = latestDraft.value
  if (field === 'tags') {
    editBuffer.value.tags = (draft.tags || []).map((t) => `#${t}`).join(' ')
  } else {
    editBuffer.value[field] = draft[field] || ''
  }
  editingField.value = field
}

function cancelEdit() {
  editingField.value = null
}

async function saveEdit(field) {
  if (!isEditableDraft.value) return
  const payload = {}
  if (field === 'tags') {
    payload.tags = (editBuffer.value.tags || '')
      .split(/[\s,，]+/)
      .map((t) => t.trim().replace(/^#+/, ''))
      .filter(Boolean)
  } else {
    payload[field] = editBuffer.value[field] || ''
  }
  savingDraft.value = true
  try {
    await api.patch(`/orders/${orderId}/drafts/${latestDraft.value.version}`, payload)
    ElMessage.success('已保存')
    editingField.value = null
    await fetchOrder({ silent: true })
  } catch (err) {
    ElMessage.error(err.response?.data?.error || '保存失败')
  } finally {
    savingDraft.value = false
  }
}

// ---------------------------------------------------------------------------
// Inline order editing — title / requirements / reference_links / content_type
// ---------------------------------------------------------------------------
function startOrderEdit(field) {
  if (!canEditOrder.value) return
  const o = order.value
  if (field === 'reference_links') {
    orderEditBuffer.value.reference_links = (o.reference_links || []).join('\n')
  } else {
    orderEditBuffer.value[field] = o[field] || ''
  }
  editingOrderField.value = field
}

function cancelOrderEdit() {
  editingOrderField.value = null
}

async function saveOrderEdit(field) {
  if (!canEditOrder.value) return
  const payload = {}
  if (field === 'reference_links') {
    payload.reference_links = (orderEditBuffer.value.reference_links || '')
      .split(/\n+/)
      .map((l) => l.trim())
      .filter(Boolean)
  } else {
    payload[field] = orderEditBuffer.value[field] || ''
  }
  savingOrder.value = true
  try {
    await api.patch(`/orders/${orderId}`, payload)
    ElMessage.success('已保存')
    editingOrderField.value = null
    await fetchOrder({ silent: true })
  } catch (err) {
    ElMessage.error(err.response?.data?.error || '保存失败')
  } finally {
    savingOrder.value = false
  }
}

// ---------------------------------------------------------------------------
// Material upload / delete
// ---------------------------------------------------------------------------
function triggerMaterialUpload() {
  materialFileInput.value?.click()
}

async function handleMaterialFilesSelected(event) {
  const files = Array.from(event.target.files || [])
  event.target.value = ''
  if (files.length === 0) return
  if (!canEditOrder.value) return

  const formData = new FormData()
  for (const f of files) formData.append('files', f)

  uploadingMaterial.value = true
  try {
    const { data } = await api.post(`/orders/${orderId}/materials`, formData)
    const addedCount = (data.materials || []).length
    if (data.mode_changed) {
      ElMessage.info(`检测到 DOCX 中包含图片，已自动切换为图文模式 (+${addedCount} 份素材)`)
    } else if (data.requirements_updated) {
      ElMessage.success(`已上传 ${addedCount} 份素材，DOCX 文字已合并进「内容要求」`)
    } else {
      ElMessage.success(`已上传 ${addedCount} 份素材`)
    }
    await fetchOrder({ silent: true })
  } catch (err) {
    ElMessage.error(err.response?.data?.error || '上传失败')
  } finally {
    uploadingMaterial.value = false
  }
}

async function handleDeleteMaterial(material) {
  if (!canEditOrder.value) return
  try {
    await ElMessageBox.confirm(`删除素材 "${material.file_name}"?`, '删除确认', { type: 'warning' })
    await api.delete(`/orders/${orderId}/materials/${material.id}`)
    ElMessage.success('已删除')
    await fetchOrder({ silent: true })
  } catch (err) {
    if (err !== 'cancel') ElMessage.error(err.response?.data?.error || '删除失败')
  }
}

// Same as handleDeleteMaterial but used by the draft-preview tile delete
// button. We intentionally do NOT gate on canEditOrder here — the draft preview
// shows whatever images will be published, and the user should be able to
// remove a bad image even after the order has moved past the "editable" state
// (e.g. draft approved but not yet scheduled). Backend still enforces auth.
async function handleDeleteDraftImage(material) {
  try {
    await ElMessageBox.confirm(`从发帖图片中移除 "${material.file_name}"?`, '移除确认', { type: 'warning' })
    await api.delete(`/orders/${orderId}/materials/${material.id}`)
    ElMessage.success('已移除')
    await fetchOrder({ silent: true })
  } catch (err) {
    if (err !== 'cancel') ElMessage.error(err.response?.data?.error || '移除失败')
  }
}

// --- Preview image drag-and-drop reordering ------------------------------
// Users can drag image tiles on the draft preview to change the publish order
// (the first image becomes the xhs cover). Optimistic update with server-side
// persistence — on failure we revert by refetching the order.
function canReorderImages() {
  return !!order.value && previewMaterials.value.length > 1 && !savingImageOrder.value
}

function onImageDragStart(material, event) {
  if (!canReorderImages()) {
    event.preventDefault()
    return
  }
  dragImageId.value = material.id
  event.dataTransfer.effectAllowed = 'move'
  // Firefox requires setData to actually start the drag.
  try { event.dataTransfer.setData('text/plain', String(material.id)) } catch {}
}

function onImageDragOver(material, event) {
  if (dragImageId.value == null) return
  event.preventDefault()
  event.dataTransfer.dropEffect = 'move'
  if (dragOverImageId.value !== material.id) {
    dragOverImageId.value = material.id
  }
}

function onImageDragLeave(material) {
  if (dragOverImageId.value === material.id) {
    dragOverImageId.value = null
  }
}

function onImageDragEnd() {
  dragImageId.value = null
  dragOverImageId.value = null
}

async function onImageDrop(target, event) {
  event.preventDefault()
  const sourceId = dragImageId.value
  dragImageId.value = null
  dragOverImageId.value = null
  if (sourceId == null || sourceId === target.id) return

  const currentImages = previewMaterials.value
  const fromIdx = currentImages.findIndex((m) => m.id === sourceId)
  const toIdx = currentImages.findIndex((m) => m.id === target.id)
  if (fromIdx === -1 || toIdx === -1 || fromIdx === toIdx) return

  // Build the new image id sequence.
  const newImageIds = currentImages.map((m) => m.id)
  const [moved] = newImageIds.splice(fromIdx, 1)
  newImageIds.splice(toIdx, 0, moved)

  // Rebuild order.value.materials optimistically: images first in the new
  // order, then the non-image materials (keeping their relative order).
  const byId = new Map((order.value?.materials || []).map((m) => [m.id, m]))
  const imageMaterialsNew = newImageIds.map((id) => byId.get(id)).filter(Boolean)
  const nonImageMaterials = (order.value?.materials || []).filter(
    (m) => !m.file_type.startsWith('image/')
  )
  const previousMaterials = order.value.materials
  order.value.materials = [...imageMaterialsNew, ...nonImageMaterials]

  savingImageOrder.value = true
  try {
    await api.put(`/orders/${orderId}/materials/order`, { ids: newImageIds })
  } catch (err) {
    // Revert optimistic change.
    order.value.materials = previousMaterials
    ElMessage.error(err.response?.data?.error || '保存图片顺序失败')
  } finally {
    savingImageOrder.value = false
  }
}

async function handleGenerateCover() {
  // description 可空 —— 后端会用最新草稿的标题+正文 + bot 画风生图
  generatingCover.value = true
  coverStatus.value = {
    state: 'running',
    startedAt: Date.now(),
    message: `调用 image-gen MCP 生成 ${Math.min(5, Math.max(1, Number(coverCount.value) || 1))} 张封面,请稍候...`,
    files: [],
    error: '',
  }
  // 立即关闭 dialog,让卡片接管 loading 状态显示。
  coverDialogVisible.value = false
  const descriptionSnapshot = coverDescription.value.trim()
  const countSnapshot = Math.min(5, Math.max(1, Number(coverCount.value) || 1))
  coverDescription.value = ''
  try {
    // 显式超时 —— image-gen MCP 单张通常 30-90s,多张按线性估算留出余量。
    const perImageMs = 120000
    const timeoutMs = Math.max(300000, perImageMs * countSnapshot + 60000)
    const { data } = await api.post(
      `/orders/${orderId}/generate-cover`,
      { description: descriptionSnapshot, count: countSnapshot },
      { timeout: timeoutMs }
    )
    const files = data.files || []
    coverStatus.value = {
      state: 'success',
      startedAt: coverStatus.value.startedAt,
      finishedAt: Date.now(),
      message: `封面已生成 ${files.length} 张,已加入素材`,
      files,
      error: '',
    }
    ElMessage.success(`封面已生成 (${files.length} 张)`)
    await fetchOrder()
  } catch (err) {
    const errMsg = err.response?.data?.error || err.message || '封面生成失败'
    coverStatus.value = {
      state: 'error',
      startedAt: coverStatus.value.startedAt,
      finishedAt: Date.now(),
      message: '封面生成失败',
      files: [],
      error: errMsg,
    }
    ElMessage.error(errMsg)
  } finally {
    generatingCover.value = false
  }
}
</script>

<template>
  <div v-loading="loading" style="max-width: 1320px; margin: 0 auto">
    <el-page-header @back="router.push('/orders')" title="返回订单列表">
      <template #content>订单详情</template>
    </el-page-header>

    <template v-if="order">
      <!-- Hidden file input used by the materials upload button -->
      <input
        ref="materialFileInput"
        type="file"
        multiple
        accept="image/jpeg,image/png,image/webp,.docx,.txt,text/plain"
        style="display: none"
        @change="handleMaterialFilesSelected"
      />

      <!-- Top header bar: 订单标题 / 达人 / 内容类型 / 状态 — spans full width -->
      <el-card class="order-top-bar" style="margin: 16px 0 20px">
        <div style="display: flex; justify-content: space-between; align-items: start; gap: 16px">
          <div style="flex: 1; min-width: 0">
            <!-- 订单标题:V1 草稿生成后由后端自动填充,不可手动编辑 -->
            <h3 style="margin: 0 0 8px">
              {{ order.title || (isFirstDraftPending ? '(订单标题生成中…)' : `订单 #${order.id.slice(0, 8)}`) }}
            </h3>
            <div style="color: #999; font-size: 13px; margin-bottom: 4px">
              达人：{{ order.bot_name || order.bot_id }} ·
              <template v-if="editingOrderField === 'content_type'">
                <el-select
                  v-model="orderEditBuffer.content_type"
                  :disabled="savingOrder"
                  size="small"
                  style="width: 130px; margin-left: 4px"
                  @change="saveOrderEdit('content_type')"
                >
                  <el-option label="文字生图" value="text_to_image" />
                  <el-option label="图文" value="image" />
                  <el-option label="长文" value="longform" />
                </el-select>
                <el-button size="small" text @click="cancelOrderEdit" style="margin-left: 4px">×</el-button>
              </template>
              <span
                v-else
                :class="{ 'editable-field': canEditOrder }"
                :title="canEditOrder ? '点击切换内容类型' : ''"
                @click="canEditOrder && startOrderEdit('content_type')"
              >{{ { text_to_image: '文字生图', image: '图文', longform: '长文' }[order.content_type] || order.content_type }}</span>
            </div>
            <div v-if="order.skill_id" style="color: #999; font-size: 13px; margin-bottom: 4px">
              服务：<el-tag size="small" type="warning">{{ skillDisplayName || order.skill_id }}</el-tag>
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

      <div class="order-detail-layout">
        <!-- Row 1, Col 1: bot capabilities snapshot -->
        <div class="grid-row1-left">
          <el-card
            v-if="botCapabilities && (botCapabilities.skills?.['研究技能']?.length || botCapabilities.skills?.['风格']?.length || botCapabilities.mcp_servers?.length)"
            class="bot-caps-card"
            shadow="hover"
            style="height: 100%"
          >
            <div class="bot-caps-bg" :style="{ backgroundImage: `url(/api/bots/${order.bot_id}/avatar)` }"></div>
            <div class="bot-caps-inner">
              <div class="bot-caps-header">
                <el-avatar :size="44" :src="`/api/bots/${order.bot_id}/avatar`">{{ (order.bot_name || order.bot_id)[0] }}</el-avatar>
                <div style="min-width: 0">
                  <div class="bot-caps-name">{{ order.bot_name || order.bot_id }}</div>
                  <div class="bot-caps-subtitle">的能力 · 只读</div>
                </div>
              </div>

              <div v-if="botCapabilities.skills?.['研究技能']?.length" class="bot-caps-section">
                <div class="bot-caps-section-title">🔬 研究技能 · {{ botCapabilities.skills['研究技能'].length }}</div>
                <div class="bot-caps-tags">
                  <el-tag
                    v-for="skill in botCapabilities.skills['研究技能']"
                    :key="skill.id"
                    size="small"
                    type="info"
                    effect="plain"
                    :title="skill.id"
                  >{{ skill.name }}</el-tag>
                </div>
              </div>

              <div v-if="botCapabilities.skills?.['风格']?.length" class="bot-caps-section">
                <div class="bot-caps-section-title">🎨 风格 · {{ botCapabilities.skills['风格'].length }}</div>
                <div class="bot-caps-tags">
                  <el-tag
                    v-for="skill in botCapabilities.skills['风格']"
                    :key="skill.id"
                    size="small"
                    type="warning"
                    effect="plain"
                    :title="skill.id"
                  >{{ skill.name }}</el-tag>
                </div>
              </div>

              <div v-if="botCapabilities.mcp_servers?.length" class="bot-caps-section">
                <div class="bot-caps-section-title">🔌 接入的 MCP · {{ botCapabilities.mcp_servers.length }}</div>
                <div class="bot-caps-tags">
                  <el-tag
                    v-for="mcp in botCapabilities.mcp_servers"
                    :key="mcp.name"
                    size="small"
                    type="success"
                    effect="plain"
                    :title="mcp.name"
                  >{{ mcp.display_name }}</el-tag>
                </div>
              </div>

            </div>
          </el-card>
        </div>

        <!-- Row 2, Col 1: chat / refine card -->
        <div class="grid-row2-left">
          <!-- 与 bot 对话生成 / 迭代草稿 -->
          <el-card v-if="canRefine || refineTurns.length > 0" class="chat-refine-card">
            <template #header>
              <div style="display: flex; justify-content: space-between; align-items: center">
                <span style="font-weight: bold">向 {{ order.bot_name || order.bot_id }} 提需求 · 生成草稿</span>
                <span :style="{ color: refineQuotaExhausted ? '#f56c6c' : '#909399', fontSize: '12px' }">
                  用量 {{ refineQuota.used }} / {{ refineQuota.max }}
                </span>
              </div>
            </template>

            <!-- 历史消息(始终渲染以占满剩余空间) -->
            <div class="chat-history">
              <div v-if="refineTurns.length === 0" style="color: #909399; font-size: 13px; line-height: 1.7; padding: 4px 6px">
                每次提交 = 生成 1 个新版本草稿。第一条消息会作为订单的"原始背景",bot 后续轮次都能看到。
                <br />你可以直接输入需求("讲一下半导体国产替代"),也可以在素材卡上传 DOCX,文字会自动作为背景。
              </div>
              <div v-for="turn in refineTurns" :key="turn.id" style="margin-bottom: 10px">
                <div style="display: flex; justify-content: flex-end; margin-bottom: 4px">
                  <div style="max-width: 85%; padding: 8px 12px; border-radius: 12px 12px 2px 12px; background: #409eff; color: #fff; font-size: 13px; line-height: 1.5; white-space: pre-wrap; word-break: break-word">
                    {{ turn.instruction }}
                  </div>
                </div>
                <div style="display: flex; justify-content: flex-start">
                  <div
                    :style="{
                      maxWidth: '85%',
                      padding: '6px 12px',
                      borderRadius: '12px 12px 12px 2px',
                      background: turn.status === 'error' ? '#fef0f0' : '#f5f7fa',
                      border: turn.status === 'error' ? '1px solid #fbc4c4' : '1px solid #ebeef5',
                      fontSize: '12px',
                      color: turn.status === 'error' ? '#f56c6c' : '#606266',
                    }"
                  >
                    <div v-if="turn.status === 'pending'" class="live-status-box" :ref="(el) => setLiveStatusBoxRef(turn.id, el)">
                      <div
                        v-if="!turn.liveStatusLines || turn.liveStatusLines.length === 0"
                        class="live-status-line"
                      >
                        <span class="live-status-dot">⏳</span> bot 生成中...
                      </div>
                      <transition-group v-else name="live-status" tag="div">
                        <div
                          v-for="(line, i) in turn.liveStatusLines"
                          :key="`${turn.id}-${line}-${i}`"
                          class="live-status-line"
                          :class="{ 'live-status-line-latest': i === turn.liveStatusLines.length - 1 }"
                        >
                          <span class="live-status-dot">
                            {{ i === turn.liveStatusLines.length - 1 ? '⏳' : '·' }}
                          </span>
                          {{ line }}
                        </div>
                      </transition-group>
                    </div>
                    <span v-else-if="turn.status === 'error'">⛔ {{ turn.error }}</span>
                    <span v-else-if="turn.draft">
                      ✅ 已生成 <el-tag type="success" size="small" style="margin: 0 4px">V{{ turn.draft.version }}</el-tag>
                      {{ turn.draft.title || '(无标题)' }}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <!-- 输入框 -->
            <el-input
              v-model="refineInput"
              type="textarea"
              :rows="4"
              :placeholder="refineQuotaExhausted ? '对话次数已达上限，请联系研究部调高' : (refineTurns.length === 0 ? '请描述你希望创作的内容，包括主题、风格、目标受众等' : '提出修改意见，例如：把标题改得更活泼一点 / 正文加一段数据支撑')"
              :disabled="refineQuotaExhausted || refineSending || !canRefine"
              maxlength="4000"
              show-word-limit
            />
            <div style="margin-top: 8px; text-align: right">
              <el-button
                type="primary"
                :loading="refineSending"
                :disabled="refineQuotaExhausted || !refineInput.trim() || !canRefine"
                @click="handleRefineSend"
              >
                {{ refineTurns.length === 0 ? '生成 V1 草稿' : '生成新版本' }}
              </el-button>
            </div>
          </el-card>
        </div>

        <!-- Row 1, Col 2: materials (+ cover) -->
        <div class="grid-row1-right">
      <el-card style="margin-bottom: 20px">
        <template #header>
          <div style="display: flex; justify-content: space-between; align-items: center">
            <span style="font-weight: bold">
              素材
              <span v-if="order.materials?.length" style="color: #c0c4cc; font-weight: normal; font-size: 13px; margin-left: 4px">
                ({{ order.materials.length }}{{ imageCount > 0 ? `，含 ${imageCount} 张图` : '' }})
              </span>
            </span>
            <el-button
              v-if="canEditOrder"
              size="small"
              type="primary"
              plain
              :loading="uploadingMaterial"
              @click="triggerMaterialUpload"
            >
              {{ uploadingMaterial ? '上传中...' : '+ 上传素材' }}
            </el-button>
          </div>
        </template>

        <div v-if="!order.materials?.length" style="color: #c0c4cc; font-size: 13px; padding: 12px 0">
          暂无素材。支持 jpg / png / webp / docx / txt,单文件 ≤ 10MB。DOCX 会自动解析文字进「内容要求」,里面包含的图片会自动切换为图文模式。
        </div>
        <div v-else style="display: flex; gap: 12px; flex-wrap: wrap">
          <div v-for="m in order.materials" :key="m.id" style="position: relative; text-align: center">
            <el-button
              v-if="canEditOrder"
              circle
              size="small"
              type="danger"
              style="position: absolute; top: -6px; right: -6px; z-index: 2; padding: 4px; min-height: auto; width: 22px; height: 22px"
              @click="handleDeleteMaterial(m)"
              title="删除素材"
            >×</el-button>
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

        <!-- 参考链接 (editable) — folded into materials card -->
        <div style="margin-top: 16px; padding-top: 12px; border-top: 1px dashed #ebeef5">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px">
            <span style="color: #999; font-size: 13px">参考链接</span>
            <el-button v-if="canEditOrder && editingOrderField !== 'reference_links'" text type="primary" size="small" @click="startOrderEdit('reference_links')">
              {{ order.reference_links?.length ? '编辑' : '+ 添加' }}
            </el-button>
          </div>
          <template v-if="editingOrderField === 'reference_links'">
            <el-input
              v-model="orderEditBuffer.reference_links"
              type="textarea"
              :rows="3"
              :disabled="savingOrder"
              placeholder="一行一个链接，留空则清空"
            />
            <div style="margin-top: 6px; text-align: right">
              <el-button size="small" :disabled="savingOrder" @click="cancelOrderEdit">取消</el-button>
              <el-button size="small" type="primary" :loading="savingOrder" @click="saveOrderEdit('reference_links')">保存</el-button>
            </div>
          </template>
          <template v-else>
            <div v-if="order.reference_links?.length">
              <div v-for="link in order.reference_links" :key="link">
                <a :href="link" target="_blank" style="color: #409eff; font-size: 13px">{{ link }}</a>
              </div>
            </div>
            <div v-else style="color: #c0c4cc; font-size: 13px">暂无参考链接</div>
          </template>
        </div>
      </el-card>

      <!-- 生成封面:独立一栏。text_to_image 模式自动生成卡片图,不需要手动生成 -->
      <el-card v-if="canGenerateCover" style="margin-bottom: 20px">
        <template #header>
          <div style="display: flex; justify-content: space-between; align-items: center">
            <span style="font-weight: bold">封面图</span>
            <el-button
              size="small"
              type="warning"
              :loading="generatingCover"
              :disabled="generatingCover"
              @click="coverDialogVisible = true"
            >
              {{ generatingCover ? '生成中...' : '生成封面' }}
            </el-button>
          </div>
        </template>
        <!-- 生成状态区:替代原来的介绍文字。
             idle → 简短提示;running → 进度条+耗时;success → 图片缩略图;error → 错误信息 -->
        <div v-if="coverStatus.state === 'idle'" style="color: #c0c4cc; font-size: 12.5px">
          点击右上角「生成封面」,使用 {{ order.bot_name || order.bot_id }} 的画风生成封面图。
        </div>

        <div v-else-if="coverStatus.state === 'running'" style="padding: 4px 0">
          <div style="display: flex; align-items: center; gap: 10px; color: #e6a23c; font-size: 13px; margin-bottom: 8px">
            <el-icon class="is-loading"><svg viewBox="0 0 1024 1024" width="14" height="14"><path fill="currentColor" d="M512 64a448 448 0 110 896 448 448 0 010-896zm0 64a384 384 0 100 768 384 384 0 000-768z"/><path fill="currentColor" d="M512 64a448 448 0 0 1 384 220l-56 32a384 384 0 0 0-328-188z"/></svg></el-icon>
            <span>{{ coverStatus.message }}</span>
            <span style="color: #c0c4cc; font-size: 12px">已等待 {{ coverElapsed }}s</span>
          </div>
          <el-progress :percentage="coverProgressPct" :show-text="false" status="warning" :stroke-width="4" />
        </div>

        <div v-else-if="coverStatus.state === 'success'" style="padding: 4px 0">
          <div style="display: flex; align-items: center; gap: 8px; color: #67c23a; font-size: 13px; margin-bottom: 10px">
            <span>✓</span>
            <span>{{ coverStatus.message }}</span>
            <span style="color: #c0c4cc; font-size: 12px">
              耗时 {{ Math.round((coverStatus.finishedAt - coverStatus.startedAt) / 1000) }}s
            </span>
          </div>
          <div v-if="coverResultFiles.length" style="display: flex; gap: 8px; flex-wrap: wrap">
            <div
              v-for="(f, idx) in coverResultFiles"
              :key="f.id || idx"
              style="width: 84px; height: 84px; border-radius: 6px; overflow: hidden; border: 1px solid #e4e7ed; background: #f5f7fa"
            >
              <el-image
                v-if="f.id && materialPreviewUrls[f.id]"
                :src="materialPreviewUrls[f.id]"
                fit="cover"
                style="width: 100%; height: 100%"
              />
              <div
                v-else
                style="width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; color: #c0c4cc; font-size: 11px"
              >
                加载中
              </div>
            </div>
          </div>
          <div style="margin-top: 8px; color: #909399; font-size: 12px">
            已加入素材,首图即默认封面。可在左侧素材区拖动排序。
          </div>
        </div>

        <div v-else-if="coverStatus.state === 'error'" style="padding: 4px 0">
          <div style="color: #f56c6c; font-size: 13px; margin-bottom: 4px">✗ {{ coverStatus.message }}</div>
          <div style="color: #909399; font-size: 12px; word-break: break-all">{{ coverStatus.error }}</div>
        </div>
      </el-card>
        </div>

        <!-- Row 2, Col 2: draft + alert + actions + schedule -->
        <div class="grid-row2-right">
      <!-- Empty state: no draft yet (or still pending) — show a friendly
           placeholder instead of leaving the right column blank. -->
      <el-card v-if="!latestDraft || latestDraft.status === 'pending'" style="margin-bottom: 20px">
        <template #header>
          <div style="display: flex; justify-content: space-between; align-items: center">
            <span style="font-weight: bold">草稿</span>
            <span style="color: #c0c4cc; font-size: 12px">尚未生成</span>
          </div>
        </template>
        <div style="padding: 36px 20px; text-align: center; color: #909399">
          <div style="font-size: 40px; line-height: 1; margin-bottom: 12px">📝</div>
          <div v-if="latestDraft?.status === 'pending'" style="font-size: 14px; color: #606266; margin-bottom: 6px">
            {{ order.bot_name || order.bot_id }} 正在生成草稿中...
          </div>
          <div v-else style="font-size: 14px; color: #606266; margin-bottom: 6px">
            还没有草稿
          </div>
          <div style="font-size: 12.5px; line-height: 1.8">
            <template v-if="latestDraft?.status === 'pending'">
              生成需要 30 秒到几分钟,完成后会自动刷新。期间可以先补充素材或参考链接。
            </template>
            <template v-else>
              在左侧「向 {{ order.bot_name || order.bot_id }} 提需求」处描述你要的内容,<br/>
              点<span style="color: #409eff">生成 V1 草稿</span>后这里会显示 bot 产出的标题、正文、标签。
            </template>
          </div>
          <div style="margin-top: 18px; font-size: 12px; color: #c0c4cc">
            草稿生成后,你可以直接点击字段修改、或者继续跟 bot 提新需求迭代。
          </div>
        </div>
      </el-card>

      <el-card v-if="latestDraft && latestDraft.status !== 'pending'" style="margin-bottom: 20px">
        <template #header>
          <div style="display: flex; justify-content: space-between; align-items: center">
            <span style="font-weight: bold">草稿</span>
            <span style="color: #c0c4cc; font-size: 12px">{{ isEditableDraft ? '点击任一字段可直接编辑' : '' }}</span>
          </div>
        </template>

        <template v-if="true">
          <!-- Body renderer: card_text → title → content → tags. Inline-editable
               when draft is the latest and in status='ready'. -->
          <div
            v-for="draft in (order.drafts.length > 1 ? order.drafts : [latestDraft])"
            :key="draft.version"
            v-show="order.drafts.length === 1 || draft.version === selectedDraftVersion"
          >
            <div v-if="order.drafts.length > 1" style="margin-bottom: 12px; display: flex; gap: 6px; flex-wrap: wrap">
              <el-tag
                v-for="d in order.drafts"
                :key="d.version"
                :type="d.version === selectedDraftVersion ? '' : 'info'"
                :effect="d.version === selectedDraftVersion ? 'dark' : 'plain'"
                style="cursor: pointer"
                @click="selectedDraftVersion = d.version"
              >
                V{{ d.version }}
              </el-tag>
              <el-tag
                :type="draft.status === 'approved' ? 'success' : draft.status === 'revision_requested' ? 'warning' : 'info'"
                size="small"
              >
                {{ { ready: '待审核', approved: '已通过', revision_requested: '已修改', superseded: '已替换', pending: '生成中', failed: '失败' }[draft.status] || draft.status }}
              </el-tag>
            </div>

            <!-- 1a. 图文/长文模式:草稿首先展示即将作为发帖的图片(来自 order.materials) -->
            <div
              v-if="order.content_type !== 'text_to_image' && previewMaterials.length"
              style="background: #f5f7fa; padding: 16px; border-radius: 8px; margin-bottom: 12px"
            >
              <div style="font-size: 12px; color: #999; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center">
                <span>发帖图片 ({{ previewMaterials.length }} 张,首图为封面)</span>
                <span v-if="previewMaterials.length > 1" style="color: #bbb; font-size: 11px">
                  拖动图片可调整顺序{{ savingImageOrder ? '(保存中...)' : '' }}
                </span>
              </div>
              <div style="display: flex; gap: 8px; flex-wrap: wrap">
                <div
                  v-for="(m, idx) in previewMaterials"
                  :key="m.id"
                  class="preview-image-tile"
                  :class="{
                    'is-dragging': dragImageId === m.id,
                    'is-drag-over': dragOverImageId === m.id && dragImageId !== m.id,
                  }"
                  :draggable="previewMaterials.length > 1"
                  @dragstart="onImageDragStart(m, $event)"
                  @dragover="onImageDragOver(m, $event)"
                  @dragleave="onImageDragLeave(m)"
                  @drop="onImageDrop(m, $event)"
                  @dragend="onImageDragEnd"
                >
                  <el-image
                    :src="materialPreviewUrls[m.id]"
                    :preview-src-list="previewSrcList"
                    :initial-index="idx"
                    fit="cover"
                    preview-teleported
                    draggable="false"
                    style="width: 100%; height: 100%; cursor: zoom-in"
                  />
                  <div
                    v-if="idx === 0"
                    style="position: absolute; top: 4px; left: 4px; background: rgba(230, 162, 60, 0.9); color: #fff; font-size: 11px; padding: 1px 6px; border-radius: 4px"
                  >封面</div>
                  <div
                    style="position: absolute; bottom: 4px; right: 4px; background: rgba(0,0,0,0.55); color: #fff; font-size: 10px; padding: 0 5px; border-radius: 3px; line-height: 14px"
                  >{{ idx + 1 }}</div>
                  <button
                    class="preview-image-delete"
                    title="移除图片"
                    style="position: absolute; top: 3px; right: 3px; width: 20px; height: 20px; border-radius: 50%; border: 1.5px solid #fff; background: #f56c6c; color: #fff; font-size: 13px; line-height: 1; cursor: pointer; padding: 0; display: flex; align-items: center; justify-content: center; z-index: 10; box-shadow: 0 1px 3px rgba(0,0,0,0.25)"
                    @click.stop="handleDeleteDraftImage(m)"
                    @mousedown.stop
                    @dragstart.stop.prevent
                  >×</button>
                </div>
              </div>
            </div>

            <!-- 1b. 卡片文字 — 仅 text_to_image 模式展示 -->
            <div
              v-if="order.content_type === 'text_to_image' && (draft.card_text || isLatestReady(draft))"
              style="background: #f5f7fa; padding: 16px; border-radius: 8px; margin-bottom: 12px"
            >
              <div style="font-size: 12px; color: #999; margin-bottom: 4px">卡片文字</div>
              <el-input
                v-if="editingField === 'card_text' && isLatestReady(draft)"
                v-model="editBuffer.card_text"
                type="textarea"
                autosize
                :disabled="savingDraft"
                placeholder="卡片文字 (text_to_image 模式下展示在封面卡片上的文字)"
              />
              <div v-if="editingField === 'card_text' && isLatestReady(draft)" style="margin-top: 6px; text-align: right">
                <el-button size="small" :disabled="savingDraft" @click="cancelEdit">取消</el-button>
                <el-button size="small" type="primary" :loading="savingDraft" @click="saveEdit('card_text')">保存</el-button>
              </div>
              <pre
                v-else
                :class="{ 'editable-field': isLatestReady(draft) }"
                :title="isLatestReady(draft) ? '点击编辑' : ''"
                style="white-space: pre-wrap; margin: 0; font-family: inherit"
                @click="isLatestReady(draft) && startEdit('card_text')"
              >{{ draft.card_text || '(点击添加卡片文字)' }}</pre>
            </div>

            <!-- 2. 标题 -->
            <div style="margin-bottom: 12px">
              <template v-if="editingField === 'title' && isLatestReady(draft)">
                <el-input
                  v-model="editBuffer.title"
                  :disabled="savingDraft"
                  maxlength="60"
                  show-word-limit
                  @keydown.enter="saveEdit('title')"
                  @keydown.esc="cancelEdit"
                />
                <div style="margin-top: 6px; text-align: right">
                  <el-button size="small" :disabled="savingDraft" @click="cancelEdit">取消</el-button>
                  <el-button size="small" type="primary" :loading="savingDraft" @click="saveEdit('title')">保存</el-button>
                </div>
              </template>
              <template v-else>
                <span
                  :class="{ 'editable-field': isLatestReady(draft) }"
                  :title="isLatestReady(draft) ? '点击编辑标题' : ''"
                  style="font-weight: bold; font-size: 16px"
                  @click="isLatestReady(draft) && startEdit('title')"
                >{{ draft.title || '(点击添加标题)' }}</span>
                <el-tag
                  v-if="order.drafts.length === 1"
                  :type="draft.status === 'approved' ? 'success' : draft.status === 'revision_requested' ? 'warning' : 'info'"
                  size="small"
                  style="margin-left: 8px"
                >
                  {{ { ready: '待审核', approved: '已通过', revision_requested: '已修改', superseded: '已替换', pending: '生成中', failed: '失败' }[draft.status] || draft.status }}
                </el-tag>
              </template>
            </div>

            <!-- 3. 正文 -->
            <div>
              <template v-if="editingField === 'content' && isLatestReady(draft)">
                <el-input
                  v-model="editBuffer.content"
                  type="textarea"
                  autosize
                  :disabled="savingDraft"
                  maxlength="5000"
                  show-word-limit
                />
                <div style="margin-top: 6px; text-align: right">
                  <el-button size="small" :disabled="savingDraft" @click="cancelEdit">取消</el-button>
                  <el-button size="small" type="primary" :loading="savingDraft" @click="saveEdit('content')">保存</el-button>
                </div>
              </template>
              <pre
                v-else
                :class="{ 'editable-field': isLatestReady(draft) }"
                :title="isLatestReady(draft) ? '点击编辑正文' : ''"
                style="white-space: pre-wrap; word-break: break-word; margin: 0; font-family: inherit; line-height: 1.8"
                @click="isLatestReady(draft) && startEdit('content')"
              >{{ draft.content || '(点击添加正文)' }}</pre>
            </div>

            <!-- 3b. 引用来源 + 自检报告 (longform only, stored in card_text) -->
            <el-collapse
              v-if="order.content_type === 'longform' && draft.card_text"
              style="margin-top: 16px"
            >
              <el-collapse-item title="引用来源 + 自检报告" name="sources">
                <pre style="white-space: pre-wrap; word-break: break-word; margin: 0; font-family: inherit; line-height: 1.8; font-size: 13px; color: #606266" v-html="linkifyText(draft.card_text)"></pre>
              </el-collapse-item>
            </el-collapse>

            <!-- 3c. 数据核查报告 (fact_check) -->
            <el-collapse
              v-if="draft.fact_check"
              style="margin-top: 12px"
            >
              <el-collapse-item name="factcheck">
                <template #title>
                  <span>数据核查报告</span>
                  <el-tag size="small" type="success" style="margin-left: 8px">fact-check</el-tag>
                </template>
                <pre style="white-space: pre-wrap; word-break: break-word; margin: 0; font-family: inherit; line-height: 1.8; font-size: 13px; color: #606266" v-html="linkifyText(draft.fact_check)"></pre>
              </el-collapse-item>
            </el-collapse>

            <!-- 4. 标签 -->
            <div style="margin-top: 12px">
              <template v-if="editingField === 'tags' && isLatestReady(draft)">
                <el-input
                  v-model="editBuffer.tags"
                  :disabled="savingDraft"
                  placeholder="多个标签用空格分隔，如: #半导体 #A股 #投资笔记"
                />
                <div style="margin-top: 6px; text-align: right">
                  <el-button size="small" :disabled="savingDraft" @click="cancelEdit">取消</el-button>
                  <el-button size="small" type="primary" :loading="savingDraft" @click="saveEdit('tags')">保存</el-button>
                </div>
              </template>
              <div
                v-else
                :class="{ 'editable-field': isLatestReady(draft) }"
                :title="isLatestReady(draft) ? '点击编辑标签' : ''"
                style="display: flex; gap: 6px; flex-wrap: wrap; min-height: 24px"
                @click="isLatestReady(draft) && startEdit('tags')"
              >
                <el-tag v-for="tag in draft.tags" :key="tag" size="small">#{{ tag }}</el-tag>
                <span v-if="!draft.tags?.length && isLatestReady(draft)" style="color: #c0c4cc; font-size: 13px">(点击添加标签)</span>
              </div>
            </div>

            <div v-if="draft.revision_note" style="margin-top: 12px; padding: 12px; background: #fff7e6; border-radius: 8px; border: 1px solid #ffe7ba">
              <div style="font-size: 12px; color: #999; margin-bottom: 4px">本轮指令 / 修改意见</div>
              <div>{{ draft.revision_note }}</div>
            </div>
          </div>
        </template>
      </el-card>

      <el-alert
        v-if="awaitingPublishReview"
        type="warning"
        :closable="false"
        show-icon
        title="等待研究部确认发布"
        description="订单已提交研究部，等研究部确认后会自动进入发布队列。这期间草稿不可再修改。"
        style="margin-bottom: 20px"
      />

      <el-card v-if="canReview || canSubmitPublish || canCancel">
        <div style="display: flex; gap: 12px; flex-wrap: wrap">
          <template v-if="canReview">
            <el-button type="success" @click="handleApprove">通过</el-button>
          </template>
          <template v-if="canSubmitPublish">
            <el-button type="primary" @click="scheduleDialogVisible = true">安排发布时间</el-button>
            <el-button type="success" :loading="submittingPublish" @click="handleSubmitPublish">提交研究部确认发布</el-button>
            <el-button plain @click="handleUnapprove">上一步</el-button>
          </template>
          <el-button v-if="canCancel" type="danger" plain @click="handleCancel">取消订单</el-button>
        </div>
      </el-card>

      <div v-if="order.schedule_at" style="margin-top: 12px; color: #999; text-align: center">
        计划发布时间：{{ formatDate(order.schedule_at) }}
      </div>
        </div><!-- /.grid-row2-right -->
      </div><!-- /.order-detail-layout -->
    </template>

    <el-dialog v-model="scheduleDialogVisible" title="安排发布时间" width="400px">
      <el-date-picker v-model="scheduleTime" type="datetime" placeholder="选择发布时间" style="width: 100%" :disabled-date="(d) => d < new Date()" />
      <template #footer>
        <el-button @click="scheduleDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSchedule">确认</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="coverDialogVisible" title="生成封面" width="500px">
      <p style="color: #666; margin: 0 0 12px">
        系统会使用该达人的专属画风生成封面图片。<br />
        <span style="color: #909399; font-size: 13px">留空则根据最新草稿的标题+正文自动生图。</span>
      </p>
      <el-input
        v-model="coverDescription"
        type="textarea"
        :rows="4"
        placeholder="可留空（将用草稿内容自动生成），或手动描述，例如：一只橙色小猫咪站在金币堆上，背景是上涨的K线图，配文'黄金起飞！'"
        maxlength="500"
        show-word-limit
      />
      <div style="margin-top: 14px; display: flex; align-items: center; gap: 10px">
        <span style="color: #606266; font-size: 13px">生成张数:</span>
        <el-input-number v-model="coverCount" :min="1" :max="5" :step="1" size="small" />
        <span style="color: #c0c4cc; font-size: 12px">张数越多耗时越长,每张约 30-60 秒</span>
      </div>
      <template #footer>
        <el-button @click="coverDialogVisible = false">取消</el-button>
        <el-button type="warning" :loading="generatingCover" @click="handleGenerateCover">
          {{ generatingCover ? '生成中...' : '生成封面' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.editable-field {
  cursor: text;
  border-radius: 4px;
  padding: 2px 4px;
  margin: -2px -4px;
  transition: background-color 0.15s;
}
.editable-field:hover {
  background-color: #f0f7ff;
  outline: 1px dashed #a0cfff;
}

/* ----- Order detail 2-column layout ----- */
.order-top-bar :deep(.el-card__body) {
  padding: 18px 22px;
}
.order-detail-layout {
  display: grid;
  grid-template-columns: 440px 1fr;
  grid-template-rows: auto 1fr;
  gap: 20px;
  align-items: stretch;
}
.grid-row1-left {
  grid-column: 1;
  grid-row: 1;
  display: flex;
  flex-direction: column;
}
.grid-row1-right {
  grid-column: 2;
  grid-row: 1;
  display: flex;
  flex-direction: column;
}
.grid-row2-left {
  grid-column: 1;
  grid-row: 2;
  /* 保持 cell 被 row2 拉高(跟随 row2-right 的草稿高度),
     chat 卡片内部通过 position:sticky 吸在视口顶部,不跟着草稿变长 */
  position: relative;
  min-height: 0;
}
.grid-row2-right {
  grid-column: 2;
  grid-row: 2;
  display: flex;
  flex-direction: column;
}
/* make the last card in a column not leave a trailing margin */
.grid-row1-right > *:last-child,
.grid-row1-left > *:last-child {
  margin-bottom: 0;
}
@media (max-width: 1200px) {
  .order-detail-layout {
    display: flex;
    flex-direction: column;
  }
}

/* Chat/refine card — sticky panel pinned to viewport, does NOT stretch with
   the (potentially long) draft on the right. Internal message history scrolls. */
.chat-refine-card {
  position: sticky;
  top: 20px;
  display: flex;
  flex-direction: column;
  /* Cap height at viewport so it never overflows screen regardless of draft length */
  max-height: calc(100vh - 40px);
  min-height: 520px;
}
.chat-refine-card :deep(.el-card__body) {
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}
.chat-refine-card .chat-history {
  flex: 1 1 auto;
  min-height: 280px;
  max-height: 100%;
  overflow-y: auto;
  padding: 10px 8px;
  margin-bottom: 12px;
  border: 1px solid #f0f2f5;
  border-radius: 8px;
  background: #fafbfc;
}
.chat-refine-card .chat-history::-webkit-scrollbar {
  width: 6px;
}
.chat-refine-card .chat-history::-webkit-scrollbar-thumb {
  background: #dcdfe6;
  border-radius: 3px;
}

/* ----- Live tool-use status box in pending chat bubble ----- */
/* Rolling up to LIVE_STATUS_MAX lines. The latest line is bold/⏳, older
   lines dim with ·. New lines slide in from the bottom, old ones fade out. */
.live-status-box {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 180px;
  /* Cap to ~5 rows (18px line-height * 5 + gaps) with scroll; newer lines
     auto-scrolled into view, wheel up reveals earlier history. */
  max-height: 105px;
  overflow-y: auto;
}
.live-status-box::-webkit-scrollbar {
  width: 6px;
}
.live-status-box::-webkit-scrollbar-thumb {
  background: #dcdfe6;
  border-radius: 3px;
}
.live-status-line {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  line-height: 1.5;
  color: #909399;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 360px;
}
.live-status-line-latest {
  color: #409eff;
  font-weight: 500;
}
.live-status-dot {
  flex-shrink: 0;
  width: 14px;
  text-align: center;
}

/* <transition-group> animation: new lines slide up from below, old ones
   fade out as they scroll off the top. */
.live-status-enter-active,
.live-status-leave-active {
  transition: all 0.28s ease;
}
.live-status-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
.live-status-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}
.live-status-leave-active {
  position: absolute;
}

/* ----- Bot capabilities sidebar card (dashboard-inspired) ----- */
.bot-caps-card {
  position: relative;
  overflow: hidden;
  background: linear-gradient(160deg, #ffffff 0%, #f7f9fc 100%);
  border: 1px solid #e4e7ed;
}
.bot-caps-card :deep(.el-card__body) {
  position: relative;
  padding: 18px 18px 16px;
}
/* Avatar watermark — 石雕隐入效果 */
.bot-caps-bg {
  position: absolute;
  inset: 0;
  background-size: 140% auto;
  background-position: center 20%;
  background-repeat: no-repeat;
  opacity: 0.12;
  filter: grayscale(100%) contrast(1.3) brightness(0.85);
  mix-blend-mode: multiply;
  pointer-events: none;
  /* faint inner shadow to sell the "carved into stone" look */
}
.bot-caps-card::after {
  content: "";
  position: absolute;
  inset: 0;
  pointer-events: none;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.6), inset 0 -40px 60px -40px rgba(0, 0, 0, 0.08);
  border-radius: inherit;
}
.bot-caps-inner {
  position: relative;
  z-index: 1;
}
.bot-caps-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-bottom: 12px;
  margin-bottom: 14px;
  border-bottom: 1px dashed #dcdfe6;
}
.bot-caps-name {
  font-weight: 600;
  font-size: 15px;
  color: #303133;
  line-height: 1.2;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.bot-caps-subtitle {
  font-size: 11px;
  color: #909399;
  margin-top: 3px;
  letter-spacing: 0.3px;
}
.bot-caps-section {
  margin-bottom: 14px;
}
.bot-caps-section:last-of-type {
  margin-bottom: 6px;
}
.bot-caps-section-title {
  font-size: 11px;
  color: #909399;
  margin-bottom: 6px;
  letter-spacing: 0.4px;
  font-weight: 500;
}
.bot-caps-tags {
  display: flex;
  gap: 5px;
  flex-wrap: wrap;
}
.bot-caps-tags :deep(.el-tag) {
  margin: 0;
}

.preview-image-tile {
  position: relative;
  width: 100px;
  height: 100px;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid #eee;
  transition: transform 0.12s ease, box-shadow 0.12s ease, border-color 0.12s ease;
  user-select: none;
}
.preview-image-tile[draggable="true"] {
  cursor: grab;
}
.preview-image-tile.is-dragging {
  opacity: 0.45;
  transform: scale(0.96);
}
.preview-image-tile.is-drag-over {
  border-color: #409eff;
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.35);
  transform: scale(1.03);
}
.preview-image-delete {
  position: absolute;
  top: 3px;
  right: 3px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border: 1.5px solid #fff;
  background: #f56c6c;
  color: #fff;
  font-size: 13px;
  line-height: 1;
  cursor: pointer;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 3;
  box-shadow: 0 1px 3px rgba(0,0,0,0.25);
}
.preview-image-delete:hover {
  background: #f78989;
}
</style>
