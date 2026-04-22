<script setup>
import { ref, nextTick, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../store/auth.js'
import { useConsultStore } from '../store/consult.js'
import api from '../api/index.js'
import { ElMessage } from 'element-plus'

const router = useRouter()
const auth = useAuthStore()
const consultStore = useConsultStore()

const userInput = ref('')
const sending = ref(false)
const liveStatusLines = ref([])
const consultResult = ref(null)
const consultError = ref('')
const editingSysPrompt = ref(false)
const sysPromptDraft = ref('')
const savingSysPrompt = ref(false)
const sysPromptExpanded = ref(false)
const quickBots = ref([])

function toggleSysPrompt() {
  if (editingSysPrompt.value) return
  sysPromptExpanded.value = !sysPromptExpanded.value
}

function startEditSysPrompt() {
  sysPromptDraft.value = auth.client?.sys_prompt || ''
  sysPromptExpanded.value = true
  editingSysPrompt.value = true
}

async function saveSysPrompt() {
  savingSysPrompt.value = true
  try {
    await api.patch('/auth/me', { sys_prompt: sysPromptDraft.value })
    auth.client.sys_prompt = sysPromptDraft.value
    editingSysPrompt.value = false
    ElMessage.success('公司规范已保存')
  } catch (err) {
    ElMessage.error(err.response?.data?.error || '保存失败')
  } finally {
    savingSysPrompt.value = false
  }
}

function cancelEditSysPrompt() {
  editingSysPrompt.value = false
  sysPromptExpanded.value = false
}

async function startConsult() {
  const msg = userInput.value.trim()
  if (!msg) return

  if (!auth.isLoggedIn) {
    ElMessage.warning('请先登录')
    router.push({ name: 'Login', query: { redirect: '/' } })
    return
  }

  sending.value = true
  liveStatusLines.value = ['连接运营顾问中…']
  consultResult.value = null
  consultError.value = ''

  try {
    const resp = await fetch('/api/consult', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
        Authorization: `Bearer ${localStorage.getItem('token') || ''}`,
      },
      body: JSON.stringify({ message: msg }),
    })

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}))
      throw new Error(err.error || `请求失败 (${resp.status})`)
    }

    const reader = resp.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      const blocks = buffer.split('\n\n')
      buffer = blocks.pop() || ''

      for (const block of blocks) {
        if (!block.trim() || block.trim() === ': hb') continue
        const lines = block.split('\n')
        let eventType = ''
        let eventData = ''
        for (const line of lines) {
          if (line.startsWith('event: ')) eventType = line.slice(7).trim()
          else if (line.startsWith('data: ')) eventData = line.slice(6)
        }
        if (!eventType || !eventData) continue

        let data
        try { data = JSON.parse(eventData) } catch { continue }

        if (eventType === 'tool_use') {
          liveStatusLines.value.push(`${data.tool}: ${data.preview || ''}`)
          await nextTick()
        } else if (eventType === 'done') {
          consultResult.value = data
          consultStore.setResult(data, msg)
        } else if (eventType === 'error') {
          consultError.value = data.message || '咨询失败'
        }
      }
    }
  } catch (err) {
    consultError.value = err.message || '网络错误'
  } finally {
    sending.value = false
  }
}

async function confirmOrder() {
  if (!consultResult.value) return

  const r = consultResult.value

  try {
    const { data } = await api.post('/orders', {
      bot_id: r.recommended_bot_id,
      content_type: r.content_type,
      requirements: userInput.value.trim(),
      guidance: r.guidance || '',
    })
    consultStore.clear()
    router.push(`/orders/${data.id}`)
  } catch (err) {
    ElMessage.error(err.response?.data?.error || '创建订单失败')
  }
}

function goMarketplace() {
  router.push('/marketplace')
}

async function goQuickBot(botId) {
  if (!auth.isLoggedIn) {
    ElMessage.warning('请先登录')
    router.push({ name: 'Login', query: { redirect: `/order/select-service/${botId}` } })
    return
  }
  try {
    const { data } = await api.get(`/bots/${botId}/offerings`)
    if (data.offerings && data.offerings.length > 0) {
      router.push(`/order/select-service/${botId}`)
    } else {
      router.push(`/order/create/${botId}`)
    }
  } catch {
    router.push(`/order/create/${botId}`)
  }
}

function reset() {
  consultResult.value = null
  consultError.value = ''
  liveStatusLines.value = []
  userInput.value = ''
  consultStore.clear()
}

onMounted(async () => {
  try {
    const { data } = await api.get('/bots')
    quickBots.value = data.slice(0, 8)
  } catch {}
})
</script>

<template>
  <div class="consult-page">
    <!-- Page header -->
    <div class="page-header">
      <h1>智能下单</h1>
      <p>描述你的内容需求，运营顾问会推荐最合适的达人</p>
    </div>

    <!-- Company sys_prompt (collapsible) -->
    <div class="sys-prompt-card" v-if="auth.isLoggedIn && !consultResult && !consultError">
      <div class="sys-prompt-header" @click="toggleSysPrompt">
        <div class="sys-prompt-left">
          <span class="sys-prompt-label">公司规范</span>
          <span v-if="!sysPromptExpanded && auth.client?.sys_prompt" class="sys-prompt-preview">
            {{ auth.client.sys_prompt.length > 40 ? auth.client.sys_prompt.slice(0, 40) + '…' : auth.client.sys_prompt }}
          </span>
          <span v-if="!sysPromptExpanded && !auth.client?.sys_prompt" class="sys-prompt-empty-hint">未设置</span>
        </div>
        <el-button text size="small" @click.stop="sysPromptExpanded ? (editingSysPrompt ? cancelEditSysPrompt() : (sysPromptExpanded = false)) : startEditSysPrompt()">
          {{ editingSysPrompt ? '收起' : sysPromptExpanded ? '收起' : (auth.client?.sys_prompt ? '编辑' : '添加') }}
        </el-button>
      </div>
      <div v-if="sysPromptExpanded" class="sys-prompt-body">
        <div v-if="!editingSysPrompt">
          <div v-if="auth.client?.sys_prompt" class="sys-prompt-text">{{ auth.client.sys_prompt }}</div>
          <div v-else class="sys-prompt-empty">未设置公司规范，达人将按默认风格创作</div>
          <div class="sys-prompt-edit-actions">
            <el-button size="small" type="primary" text @click="startEditSysPrompt">编辑</el-button>
          </div>
        </div>
        <div v-else>
          <el-input
            v-model="sysPromptDraft"
            type="textarea"
            :rows="4"
            placeholder="输入贵公司的内容规范，例如：品牌调性要求、禁用词、合规要求等。所有达人创作时都会遵守此规范。"
            :maxlength="5000"
            show-word-limit
          />
          <div class="sys-prompt-edit-actions">
            <el-button size="small" @click="cancelEditSysPrompt">取消</el-button>
            <el-button size="small" type="primary" @click="saveSysPrompt" :loading="savingSysPrompt">保存</el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- Input area -->
    <div class="consult-input-card" v-if="!consultResult && !consultError">
      <div class="card-accent" />
      <el-input
        v-model="userInput"
        type="textarea"
        :rows="5"
        placeholder="例如：帮我写一篇关于黄金投资策略的小红书笔记，目标人群是年轻上班族…"
        :maxlength="4000"
        show-word-limit
        :disabled="sending"
      />
      <div class="consult-input-actions">
        <el-button @click="goMarketplace" :disabled="sending">手动选择达人</el-button>
        <el-button type="primary" @click="startConsult" :loading="sending" :disabled="!userInput.trim()">
          {{ sending ? '咨询中…' : '开始咨询' }}
        </el-button>
      </div>
    </div>

    <!-- Quick bots -->
    <div class="quick-bots" v-if="!sending && !consultResult && !consultError && quickBots.length > 0">
      <span class="quick-bots-label">或直接选择达人</span>
      <div class="quick-bots-list">
        <div
          v-for="bot in quickBots"
          :key="bot.bot_id"
          class="quick-bot-chip"
          @click="goQuickBot(bot.bot_id)"
        >
          <el-avatar :size="28" :src="`/api/bots/${bot.bot_id}/avatar`">
            {{ (bot.display_name || '?')[0] }}
          </el-avatar>
          <span class="quick-bot-name">{{ bot.display_name }}</span>
        </div>
      </div>
    </div>

    <!-- Live status -->
    <div class="live-status-card" v-if="sending && liveStatusLines.length > 0">
      <div class="live-status-header">运营顾问正在分析…</div>
      <div class="live-status-lines">
        <div
          v-for="(line, idx) in liveStatusLines"
          :key="idx"
          class="live-status-line"
        >
          <span class="live-dot">{{ idx === liveStatusLines.length - 1 ? '⏳' : '·' }}</span>
          {{ line }}
        </div>
      </div>
    </div>

    <!-- Error -->
    <div class="consult-error-card" v-if="consultError">
      <p>{{ consultError }}</p>
      <el-button @click="reset">重新咨询</el-button>
    </div>

    <!-- Result -->
    <div class="consult-result-card" v-if="consultResult">
      <div class="result-header">推荐达人</div>

      <div class="result-bot">
        <el-avatar
          :size="56"
          :src="consultResult.bot_avatar ? `/api/bots/${consultResult.recommended_bot_id}/avatar` : undefined"
          class="result-avatar"
        >
          {{ (consultResult.bot_name || '?')[0] }}
        </el-avatar>
        <div class="result-bot-meta">
          <div class="result-bot-name">{{ consultResult.bot_name }}</div>
          <div class="result-bot-id">{{ consultResult.recommended_bot_id }}</div>
        </div>
        <el-tag type="info" size="small">{{ consultResult.content_type }}</el-tag>
      </div>

      <div class="result-section">
        <div class="result-label">推荐理由</div>
        <div class="result-text">{{ consultResult.reason }}</div>
      </div>

      <div class="result-section">
        <div class="result-label">内容指导方案</div>
        <div class="result-guidance">{{ consultResult.guidance }}</div>
      </div>

      <div class="result-actions">
        <el-button @click="reset">重新咨询</el-button>
        <el-button @click="goMarketplace">手动选择其他达人</el-button>
        <el-button type="primary" size="large" @click="confirmOrder">确认下单</el-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.consult-page {
  max-width: 800px;
  margin: 0 auto;
  padding: 8px 0 40px;
}

.page-header {
  text-align: center;
  padding: 24px 0 20px;
  margin-bottom: 20px;
}

.page-header h1 {
  margin: 0 0 8px;
  font-size: 28px;
  font-weight: 700;
  color: #303133;
}

.page-header p {
  margin: 0;
  font-size: 15px;
  color: #909399;
}

/* sys_prompt collapsible card */
.sys-prompt-card {
  background: #fff;
  border-radius: 16px;
  padding: 14px 20px;
  margin-bottom: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  transition: box-shadow 0.2s;
}

.sys-prompt-card:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.07);
}

.sys-prompt-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  user-select: none;
}

.sys-prompt-left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  overflow: hidden;
}

.sys-prompt-label {
  font-size: 13px;
  font-weight: 600;
  color: #606266;
  flex-shrink: 0;
}

.sys-prompt-preview {
  font-size: 13px;
  color: #909399;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sys-prompt-empty-hint {
  font-size: 13px;
  color: #c0c4cc;
}

.sys-prompt-body {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #f2f3f5;
}

.sys-prompt-text {
  font-size: 14px;
  color: #444;
  line-height: 1.6;
  white-space: pre-wrap;
  background: #f8f9fc;
  border-radius: 8px;
  padding: 10px 14px;
  max-height: 120px;
  overflow-y: auto;
}

.sys-prompt-empty {
  font-size: 13px;
  color: #bbb;
}

.sys-prompt-edit-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 10px;
}

/* Input card with accent bar */
.consult-input-card {
  background: #fff;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  overflow: hidden;
}

.card-accent {
  height: 4px;
  border-radius: 2px;
  background: linear-gradient(90deg, #f7c75c, #e6a23c);
  margin: -24px -24px 20px;
}

.consult-input-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 16px;
}

/* Quick bots */
.quick-bots {
  margin-top: 16px;
  padding: 0 4px;
}

.quick-bots-label {
  display: block;
  font-size: 13px;
  color: #909399;
  margin-bottom: 10px;
}

.quick-bots-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.quick-bot-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px 6px 6px;
  border-radius: 999px;
  background: #fff;
  border: 1px solid #e8eaed;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 13px;
  color: #303133;
}

.quick-bot-chip:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  border-color: #e6a23c;
}

.quick-bot-name {
  white-space: nowrap;
}

/* Live status */
.live-status-card {
  background: #fff;
  border-radius: 16px;
  padding: 20px 24px;
  margin-top: 16px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
}

.live-status-header {
  font-weight: 600;
  margin-bottom: 12px;
  color: #333;
}

.live-status-lines {
  max-height: 160px;
  overflow-y: auto;
  font-size: 13px;
  color: #666;
  line-height: 1.8;
}

.live-status-line {
  display: flex;
  align-items: center;
  gap: 6px;
}

.live-dot {
  flex-shrink: 0;
  width: 18px;
  text-align: center;
}

/* Error */
.consult-error-card {
  background: #fff3f3;
  border: 1px solid #ffd4d4;
  border-radius: 16px;
  padding: 24px;
  margin-top: 16px;
  text-align: center;
  color: #d32;
}

/* Result */
.consult-result-card {
  background: #fff;
  border-radius: 16px;
  padding: 24px;
  margin-top: 16px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
}

.result-header {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 16px;
  color: #333;
}

.result-bot {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 20px;
  padding: 16px;
  border-radius: 12px;
  background: #f8f9fc;
}

.result-avatar {
  border: 2px solid rgba(247, 199, 92, 0.4);
  flex-shrink: 0;
}

.result-bot-meta {
  flex: 1;
}

.result-bot-name {
  font-size: 18px;
  font-weight: 600;
  color: #333;
}

.result-bot-id {
  font-size: 12px;
  color: #999;
  margin-top: 2px;
}

.result-section {
  margin-bottom: 16px;
}

.result-label {
  font-size: 13px;
  font-weight: 600;
  color: #999;
  margin-bottom: 6px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.result-text {
  font-size: 15px;
  color: #333;
  line-height: 1.6;
}

.result-guidance {
  font-size: 14px;
  color: #444;
  line-height: 1.7;
  white-space: pre-wrap;
  background: #f8f9fc;
  border-radius: 8px;
  padding: 14px 16px;
  max-height: 300px;
  overflow-y: auto;
}

.result-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid #eee;
}

@media (max-width: 768px) {
  .page-header h1 {
    font-size: 24px;
  }

  .result-actions {
    flex-direction: column;
  }

  .quick-bots-list {
    gap: 6px;
  }
}
</style>
