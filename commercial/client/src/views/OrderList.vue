<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api/index.js'
import { ElMessage } from 'element-plus'

const router = useRouter()
const orders = ref([])
const total = ref(0)
const loading = ref(true)
const page = ref(1)
const statusFilter = ref('')

const statusMap = {
  pending: { label: '待生成', type: 'info' },
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

async function fetchOrders() {
  loading.value = true
  try {
    const params = { page: page.value, limit: 20 }
    if (statusFilter.value) params.status = statusFilter.value
    const { data } = await api.get('/orders', { params })
    orders.value = data.orders
    total.value = data.total
  } catch (err) {
    ElMessage.error('加载订单失败')
  } finally {
    loading.value = false
  }
}

onMounted(fetchOrders)
watch([page, statusFilter], fetchOrders)

function viewOrder(row) {
  router.push(`/orders/${row.id}`)
}
</script>

<template>
  <div style="max-width: 1000px; margin: 0 auto">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px">
      <h2 style="margin: 0">我的订单</h2>
      <el-select v-model="statusFilter" placeholder="按状态筛选" clearable style="width: 150px">
        <el-option v-for="(val, key) in statusMap" :key="key" :label="val.label" :value="key" />
      </el-select>
    </div>

    <el-table :data="orders" v-loading="loading" @row-click="viewOrder" style="cursor: pointer" stripe>
      <el-table-column label="订单标题" prop="title" min-width="180">
        <template #default="{ row }">
          {{ row.title || '(未命名)' }}
        </template>
      </el-table-column>
      <el-table-column label="达人" prop="bot_name" width="120" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusMap[row.status]?.type || 'info'" size="small">
            {{ statusMap[row.status]?.label || row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="内容类型" width="100">
        <template #default="{ row }">
          {{ { text_to_image: '图文卡片', image: '图文', longform: '长文' }[row.content_type] || row.content_type }}
        </template>
      </el-table-column>
      <el-table-column label="创建时间" width="180">
        <template #default="{ row }">
          {{ new Date(row.created_at + 'Z').toLocaleString('zh-CN') }}
        </template>
      </el-table-column>
    </el-table>

    <div style="display: flex; justify-content: center; margin-top: 20px">
      <el-pagination v-model:current-page="page" :total="total" :page-size="20" layout="prev, pager, next" />
    </div>

    <el-empty v-if="!loading && orders.length === 0" description="暂无订单" />
  </div>
</template>
