<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../api/index.js'
import { ElMessage, ElMessageBox } from 'element-plus'

const clients = ref([])
const loading = ref(true)
const searchQuery = ref('')
const selectedRows = ref([])

const showCreateDialog = ref(false)
const createForm = ref({ username: '', password: '', display_name: '', company: '', phone: '', role: 'client' })
const createLoading = ref(false)

const showEditDialog = ref(false)
const editForm = ref({ id: null, display_name: '', company: '', phone: '', role: 'client' })
const editLoading = ref(false)

const showResetDialog = ref(false)
const resetForm = ref({ id: null, username: '', password: '' })
const resetLoading = ref(false)

const showBotAccessDialog = ref(false)
const botAccessForm = ref({ id: null, username: '', mode: 'all', bot_ids: [] })
const botAccessLoading = ref(false)
const botQuotas = ref({})
const allBots = ref([])

const showBatchBotDialog = ref(false)
const batchBotForm = ref({ mode: 'all', bot_ids: [] })
const batchBotLoading = ref(false)

const currentPage = ref(1)
const pageSize = ref(20)
const sortKey = ref('')
const sortOrder = ref('')

function formatTime(t) {
  if (!t) return '-'
  return t.replace('T', ' ').slice(0, 16)
}

const filteredClients = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  let list = clients.value
  if (q) {
    list = list.filter((c) =>
      c.username.toLowerCase().includes(q) ||
      (c.display_name || '').toLowerCase().includes(q) ||
      (c.company || '').toLowerCase().includes(q) ||
      (c.phone || '').includes(q)
    )
  }
  if (sortKey.value && sortOrder.value) {
    const key = sortKey.value
    const asc = sortOrder.value === 'ascending'
    list = [...list].sort((a, b) => {
      const va = a[key] ?? ''
      const vb = b[key] ?? ''
      let cmp
      if (typeof va === 'number' && typeof vb === 'number') {
        cmp = va - vb
      } else {
        cmp = String(va).localeCompare(String(vb), 'zh')
      }
      return asc ? cmp : -cmp
    })
  }
  return list
})

const pagedClients = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return filteredClients.value.slice(start, start + pageSize.value)
})

function handleSortChange({ prop, order }) {
  sortKey.value = prop || ''
  sortOrder.value = order || ''
}

function handleSelectionChange(rows) {
  selectedRows.value = rows
}

async function fetchClients() {
  loading.value = true
  try {
    const { data } = await api.get('/admin/clients')
    clients.value = data.clients
  } catch (err) {
    ElMessage.error(err.response?.data?.error || '加载失败')
  } finally {
    loading.value = false
  }
}

async function fetchAllBots() {
  try {
    const { data } = await api.get('/bots')
    allBots.value = data
  } catch {}
}

function botDisplayName(botId) {
  const bot = allBots.value.find((b) => b.bot_id === botId)
  return bot?.display_name || botId
}

function openCreate() {
  createForm.value = { username: '', password: '', display_name: '', company: '', phone: '', role: 'client' }
  showCreateDialog.value = true
}

async function createClient() {
  const f = createForm.value
  if (!f.username || !f.password || !f.display_name) {
    return ElMessage.warning('用户名、密码、昵称为必填')
  }
  createLoading.value = true
  try {
    await api.post('/admin/clients', f)
    ElMessage.success('创建成功')
    showCreateDialog.value = false
    fetchClients()
  } catch (err) {
    ElMessage.error(err.response?.data?.error || '创建失败')
  } finally {
    createLoading.value = false
  }
}

function openEdit(row) {
  editForm.value = { id: row.id, display_name: row.display_name, company: row.company || '', phone: row.phone || '', role: row.role || 'client' }
  showEditDialog.value = true
}

async function updateClient() {
  editLoading.value = true
  try {
    await api.patch(`/admin/clients/${editForm.value.id}`, editForm.value)
    ElMessage.success('更新成功')
    showEditDialog.value = false
    fetchClients()
  } catch (err) {
    ElMessage.error(err.response?.data?.error || '更新失败')
  } finally {
    editLoading.value = false
  }
}

function openReset(row) {
  resetForm.value = { id: row.id, username: row.username, password: '' }
  showResetDialog.value = true
}

async function resetPassword() {
  if (!resetForm.value.password || resetForm.value.password.length < 4) {
    return ElMessage.warning('密码至少 4 位')
  }
  resetLoading.value = true
  try {
    await api.post(`/admin/clients/${resetForm.value.id}/reset-password`, { password: resetForm.value.password })
    ElMessage.success('密码已重置')
    showResetDialog.value = false
  } catch (err) {
    ElMessage.error(err.response?.data?.error || '重置失败')
  } finally {
    resetLoading.value = false
  }
}

async function deleteClient(row) {
  try {
    await ElMessageBox.confirm(`确定删除用户「${row.display_name}」(${row.username})？该用户的所有订单也将被删除，此操作不可恢复。`, '删除用户', { type: 'error', confirmButtonText: '确认删除', cancelButtonText: '取消' })
  } catch { return }
  try {
    await api.delete(`/admin/clients/${row.id}`)
    ElMessage.success('已删除')
    fetchClients()
  } catch (err) {
    ElMessage.error(err.response?.data?.error || '删除失败')
  }
}

async function toggleStatus(row) {
  const newStatus = row.status === 'active' ? 'disabled' : 'active'
  const label = newStatus === 'active' ? '启用' : '停用'
  try {
    await ElMessageBox.confirm(`确定${label}用户「${row.display_name}」？`, '提示', { type: 'warning' })
  } catch { return }
  try {
    await api.patch(`/admin/clients/${row.id}`, { status: newStatus })
    ElMessage.success(`已${label}`)
    fetchClients()
  } catch (err) {
    ElMessage.error(err.response?.data?.error || '操作失败')
  }
}

async function openBotAccess(row) {
  botAccessForm.value = { id: row.id, username: row.username, mode: row.bot_access_mode || 'all', bot_ids: [] }
  botQuotas.value = {}
  showBotAccessDialog.value = true
  botAccessLoading.value = true
  try {
    if (allBots.value.length === 0) await fetchAllBots()
    const [accessRes, quotaRes] = await Promise.all([
      api.get(`/admin/clients/${row.id}/bot-access`),
      api.get(`/admin/clients/${row.id}/quota`),
    ])
    botAccessForm.value.mode = accessRes.data.mode
    botAccessForm.value.bot_ids = accessRes.data.bot_ids
    const qMap = {}
    for (const q of quotaRes.data.quotas) {
      qMap[q.bot_id] = { used_count: q.used_count, max_count: q.max_count }
    }
    for (const bot of allBots.value) {
      if (!qMap[bot.bot_id]) {
        qMap[bot.bot_id] = { used_count: 0, max_count: 50 }
      }
    }
    botQuotas.value = qMap
  } catch (err) {
    ElMessage.error(err.response?.data?.error || '加载权限失败')
  } finally {
    botAccessLoading.value = false
  }
}

async function saveBotAccess() {
  botAccessLoading.value = true
  try {
    await api.put(`/admin/clients/${botAccessForm.value.id}/bot-access`, {
      mode: botAccessForm.value.mode,
      bot_ids: botAccessForm.value.bot_ids,
    })
    const quotaPromises = []
    for (const bot of allBots.value) {
      const q = botQuotas.value[bot.bot_id]
      if (q) {
        quotaPromises.push(
          api.patch(`/admin/clients/${botAccessForm.value.id}/quota`, {
            bot_id: bot.bot_id,
            max_count: q.max_count,
          })
        )
      }
    }
    await Promise.all(quotaPromises)
    ElMessage.success('Bot 权限与配额已更新')
    showBotAccessDialog.value = false
    fetchClients()
  } catch (err) {
    ElMessage.error(err.response?.data?.error || '保存失败')
  } finally {
    botAccessLoading.value = false
  }
}

async function resetBotQuota(botId) {
  try {
    await api.patch(`/admin/clients/${botAccessForm.value.id}/quota`, {
      bot_id: botId,
      reset: true,
    })
    botQuotas.value[botId].used_count = 0
    ElMessage.success(`${botDisplayName(botId)} 已用次数已重置`)
  } catch (err) {
    ElMessage.error(err.response?.data?.error || '重置失败')
  }
}

// --- Batch operations ---

function openBatchBotAccess() {
  if (allBots.value.length === 0) fetchAllBots()
  batchBotForm.value = { mode: 'all', bot_ids: [] }
  showBatchBotDialog.value = true
}

async function saveBatchBotAccess() {
  batchBotLoading.value = true
  let ok = 0
  let fail = 0
  for (const row of selectedRows.value) {
    try {
      await api.put(`/admin/clients/${row.id}/bot-access`, {
        mode: batchBotForm.value.mode,
        bot_ids: batchBotForm.value.bot_ids,
      })
      ok++
    } catch {
      fail++
    }
  }
  batchBotLoading.value = false
  showBatchBotDialog.value = false
  ElMessage.success(`Bot 权限已更新 ${ok} 人${fail ? `，${fail} 人失败` : ''}`)
  fetchClients()
}

async function batchSetStatus(status) {
  const label = status === 'active' ? '启用' : '停用'
  const names = selectedRows.value.map((r) => r.display_name).join('、')
  try {
    await ElMessageBox.confirm(`确定批量${label} ${selectedRows.value.length} 个用户（${names}）？`, '批量操作', { type: 'warning' })
  } catch { return }
  let ok = 0
  let fail = 0
  for (const row of selectedRows.value) {
    try {
      await api.patch(`/admin/clients/${row.id}`, { status })
      ok++
    } catch {
      fail++
    }
  }
  ElMessage.success(`已${label} ${ok} 人${fail ? `，${fail} 人失败` : ''}`)
  fetchClients()
}

async function batchDelete() {
  const targets = selectedRows.value.filter((r) => r.status === 'disabled')
  const skipped = selectedRows.value.length - targets.length
  if (targets.length === 0) {
    return ElMessage.warning('只能删除已停用的用户，请先批量停用')
  }
  const names = targets.map((r) => `${r.display_name}(${r.username})`).join('、')
  const skipHint = skipped > 0 ? `（${skipped} 个启用中的用户将跳过）` : ''
  try {
    await ElMessageBox.confirm(`确定删除 ${targets.length} 个用户（${names}）？${skipHint}相关订单也将一并删除，此操作不可恢复。`, '批量删除', { type: 'error', confirmButtonText: '确认删除', cancelButtonText: '取消' })
  } catch { return }
  let ok = 0
  let fail = 0
  for (const row of targets) {
    try {
      await api.delete(`/admin/clients/${row.id}`)
      ok++
    } catch {
      fail++
    }
  }
  ElMessage.success(`已删除 ${ok} 人${fail ? `，${fail} 人失败` : ''}`)
  fetchClients()
}

onMounted(() => {
  fetchClients()
  fetchAllBots()
})
</script>

<template>
  <div class="admin-clients">
    <div class="header-row">
      <h2>用户管理</h2>
      <div class="header-actions">
        <el-input
          v-model="searchQuery"
          placeholder="搜索用户名 / 昵称 / 公司"
          clearable
          style="width: 260px"
          @input="currentPage = 1"
        >
          <template #prefix>
            <el-icon><svg viewBox="0 0 1024 1024" width="14" height="14"><path d="M909.6 854.5L649.9 594.8C690.2 542.7 714 478.4 714 408c0-167.4-135.6-303-303-303S108 240.6 108 408s135.6 303 303 303c70.3 0 134.7-23.8 186.8-63.8l260 260c5.5 5.5 12.7 8.3 19.9 8.3s14.3-2.8 19.8-8.3c11-11 11-28.7 0.1-39.7zM411 667c-142.4 0-258-115.6-258-258s115.6-258 258-258 258 115.6 258 258-115.6 258-258 258z" fill="currentColor"/></svg></el-icon>
          </template>
        </el-input>
        <el-button type="primary" @click="openCreate">新建用户</el-button>
      </div>
    </div>

    <!-- Batch action bar -->
    <div class="batch-bar" v-if="selectedRows.length > 0">
      <span class="batch-info">已选 {{ selectedRows.length }} 个用户</span>
      <el-button size="small" type="primary" @click="openBatchBotAccess">批量设置 Bot 权限</el-button>
      <el-button size="small" type="warning" @click="batchSetStatus('disabled')">批量停用</el-button>
      <el-button size="small" type="success" @click="batchSetStatus('active')">批量启用</el-button>
      <el-button size="small" type="danger" @click="batchDelete">批量删除</el-button>
    </div>

    <el-table :data="pagedClients" v-loading="loading" stripe border highlight-current-row @sort-change="handleSortChange" @selection-change="handleSelectionChange">
      <el-table-column type="selection" width="40" />
      <el-table-column label="ID" prop="id" width="50" sortable="custom" />
      <el-table-column label="用户名" prop="username" width="100" sortable="custom" />
      <el-table-column label="昵称" prop="display_name" width="90" sortable="custom" />
      <el-table-column label="公司" prop="company" width="100" show-overflow-tooltip sortable="custom" />
      <el-table-column label="角色" prop="role" width="85" align="center" sortable="custom">
        <template #default="{ row }">
          <el-tag :type="row.role === 'admin' ? 'warning' : row.role === 'internal' ? 'success' : 'info'" size="small">
            {{ row.role === 'admin' ? '管理员' : row.role === 'internal' ? '内部人员' : '客户' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="可用 Bot" min-width="150">
        <template #default="{ row }">
          <template v-if="row.bot_access_mode === 'all'">
            <el-tag size="small">全部</el-tag>
          </template>
          <template v-else-if="row.allowed_bots && row.allowed_bots.length">
            <el-tag v-for="b in row.allowed_bots" :key="b" size="small" type="warning" style="margin: 0 4px 2px 0">
              {{ botDisplayName(b) }}
            </el-tag>
          </template>
          <span v-else style="color: #c0c4cc; font-size: 12px">未分配</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" prop="status" width="65" align="center" sortable="custom">
        <template #default="{ row }">
          <el-tag :type="row.status === 'active' ? 'success' : 'danger'" size="small">
            {{ row.status === 'active' ? '启用' : '停用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="创建时间" prop="created_at" width="135" sortable="custom">
        <template #default="{ row }">
          <span style="font-size: 12px; color: #909399">{{ formatTime(row.created_at) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="更新时间" prop="updated_at" width="135" sortable="custom">
        <template #default="{ row }">
          <span style="font-size: 12px; color: #909399">{{ formatTime(row.updated_at) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="270" fixed="right">
        <template #default="{ row }">
          <el-button link size="small" @click="openEdit(row)">编辑</el-button>
          <el-button link size="small" type="primary" @click="openBotAccess(row)">Bot权限</el-button>
          <el-button link size="small" type="warning" @click="openReset(row)">重置密码</el-button>
          <el-button link size="small" :type="row.status === 'active' ? 'danger' : 'success'" @click="toggleStatus(row)">
            {{ row.status === 'active' ? '停用' : '启用' }}
          </el-button>
          <el-button link size="small" type="danger" :disabled="row.status === 'active'" @click="deleteClient(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination-row">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50]"
        :total="filteredClients.length"
        layout="total, sizes, prev, pager, next"
        background
        small
      />
    </div>

    <!-- 新建用户 -->
    <el-dialog v-model="showCreateDialog" title="新建用户" width="480px" destroy-on-close>
      <el-form label-width="80px">
        <el-form-item label="用户名">
          <el-input v-model="createForm.username" placeholder="登录用户名" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="createForm.password" type="password" placeholder="至少 4 位" show-password />
        </el-form-item>
        <el-form-item label="昵称">
          <el-input v-model="createForm.display_name" placeholder="显示名称" />
        </el-form-item>
        <el-form-item label="公司">
          <el-input v-model="createForm.company" placeholder="选填" />
        </el-form-item>
        <el-form-item label="电话">
          <el-input v-model="createForm.phone" placeholder="选填" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="createForm.role" style="width: 100%">
            <el-option label="客户" value="client" />
            <el-option label="内部人员" value="internal" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" :loading="createLoading" @click="createClient">确认创建</el-button>
      </template>
    </el-dialog>

    <!-- 编辑用户 -->
    <el-dialog v-model="showEditDialog" title="编辑用户" width="480px" destroy-on-close>
      <el-form label-width="80px">
        <el-form-item label="昵称">
          <el-input v-model="editForm.display_name" />
        </el-form-item>
        <el-form-item label="公司">
          <el-input v-model="editForm.company" />
        </el-form-item>
        <el-form-item label="电话">
          <el-input v-model="editForm.phone" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="editForm.role" style="width: 100%">
            <el-option label="客户" value="client" />
            <el-option label="内部人员" value="internal" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" :loading="editLoading" @click="updateClient">保存</el-button>
      </template>
    </el-dialog>

    <!-- 重置密码 -->
    <el-dialog v-model="showResetDialog" title="重置密码" width="400px" destroy-on-close>
      <p style="margin: 0 0 16px; color: #909399">为用户 <b>{{ resetForm.username }}</b> 设置新密码</p>
      <el-input v-model="resetForm.password" type="password" placeholder="新密码（至少 4 位）" show-password />
      <template #footer>
        <el-button @click="showResetDialog = false">取消</el-button>
        <el-button type="warning" :loading="resetLoading" @click="resetPassword">确认重置</el-button>
      </template>
    </el-dialog>

    <!-- Bot 权限 (single) -->
    <el-dialog v-model="showBotAccessDialog" title="Bot 权限与配额" width="620px" destroy-on-close>
      <div v-loading="botAccessLoading">
        <p style="margin: 0 0 16px; color: #606266">
          用户 <b>{{ botAccessForm.username }}</b>
        </p>
        <el-form label-width="90px">
          <el-form-item label="访问模式">
            <el-radio-group v-model="botAccessForm.mode">
              <el-radio value="all">全部 Bot</el-radio>
              <el-radio value="restricted">指定 Bot</el-radio>
            </el-radio-group>
          </el-form-item>
        </el-form>

        <div class="quota-section-title">Bot 使用配额</div>
        <el-table :data="allBots" size="small" border style="width: 100%">
          <el-table-column label="Bot" min-width="140">
            <template #default="{ row }">
              <div style="display: flex; align-items: center; gap: 6px">
                <el-checkbox
                  v-if="botAccessForm.mode === 'restricted'"
                  :model-value="botAccessForm.bot_ids.includes(row.bot_id)"
                  @change="(val) => {
                    if (val) botAccessForm.bot_ids.push(row.bot_id)
                    else botAccessForm.bot_ids = botAccessForm.bot_ids.filter(id => id !== row.bot_id)
                  }"
                  style="margin-right: 2px"
                />
                <span>{{ row.display_name || row.bot_id }}</span>
                <span style="color: #909399; font-size: 11px">({{ row.bot_id }})</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="已用" width="70" align="center">
            <template #default="{ row }">
              {{ botQuotas[row.bot_id]?.used_count ?? 0 }}
            </template>
          </el-table-column>
          <el-table-column label="上限" width="110" align="center">
            <template #default="{ row }">
              <el-input-number
                v-if="botQuotas[row.bot_id]"
                v-model="botQuotas[row.bot_id].max_count"
                :min="1"
                :max="10000"
                size="small"
                controls-position="right"
                style="width: 90px"
              />
            </template>
          </el-table-column>
          <el-table-column label="" width="70" align="center">
            <template #default="{ row }">
              <el-button link size="small" type="warning" @click="resetBotQuota(row.bot_id)" :disabled="!botQuotas[row.bot_id]?.used_count">
                归零
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <template #footer>
        <el-button @click="showBotAccessDialog = false">取消</el-button>
        <el-button type="primary" :loading="botAccessLoading" @click="saveBotAccess">保存</el-button>
      </template>
    </el-dialog>

    <!-- Bot 权限 (batch) -->
    <el-dialog v-model="showBatchBotDialog" title="批量设置 Bot 权限" width="520px" destroy-on-close>
      <p style="margin: 0 0 12px; color: #606266">
        为 <b>{{ selectedRows.length }}</b> 个选中用户统一设置 Bot 权限
      </p>
      <el-form label-width="90px">
        <el-form-item label="访问模式">
          <el-radio-group v-model="batchBotForm.mode">
            <el-radio value="all">全部 Bot</el-radio>
            <el-radio value="restricted">指定 Bot</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="batchBotForm.mode === 'restricted'" label="允许使用">
          <el-checkbox-group v-model="batchBotForm.bot_ids">
            <div v-for="bot in allBots" :key="bot.bot_id" style="margin-bottom: 6px">
              <el-checkbox :value="bot.bot_id">
                {{ bot.display_name || bot.bot_id }}
                <span style="color: #909399; font-size: 12px; margin-left: 4px">({{ bot.bot_id }})</span>
              </el-checkbox>
            </div>
          </el-checkbox-group>
          <div v-if="allBots.length === 0" style="color: #c0c4cc; font-size: 13px">
            暂无可用 Bot
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showBatchBotDialog = false">取消</el-button>
        <el-button type="primary" :loading="batchBotLoading" @click="saveBatchBotAccess">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.admin-clients {
  padding: 0 24px;
}
.admin-clients :deep(.el-table__body tr:hover > td) {
  background-color: #ecf5ff !important;
}
.admin-clients :deep(.el-table__body tr.current-row > td) {
  background-color: #d9ecff !important;
}
.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.header-row h2 {
  margin: 0;
  font-size: 20px;
  color: #303133;
}
.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}
.batch-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
  padding: 10px 16px;
  background: #ecf5ff;
  border: 1px solid #b3d8ff;
  border-radius: 6px;
}
.batch-info {
  font-size: 13px;
  color: #409eff;
  font-weight: 500;
  margin-right: 4px;
}
.pagination-row {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}
.quota-section-title {
  font-size: 13px;
  font-weight: 600;
  color: #606266;
  margin: 12px 0 8px;
  padding-top: 12px;
  border-top: 1px solid #ebeef5;
}
</style>
