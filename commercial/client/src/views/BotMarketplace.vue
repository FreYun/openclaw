<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../store/auth.js'
import api from '../api/index.js'
import { ElMessage } from 'element-plus'

const featuredBotIds = ['bot1', 'bot2', 'bot3', 'bot4', 'bot5', 'bot6', 'bot7', 'bot12', 'bot13', 'bot17']

const router = useRouter()
const auth = useAuthStore()
const bots = ref([])
const loading = ref(true)

const orderedBots = computed(() => {
  const priority = new Map(featuredBotIds.map((id, index) => [id, index]))
  return [...bots.value].sort((a, b) => {
    const aPriority = priority.has(a.bot_id) ? priority.get(a.bot_id) : Number.MAX_SAFE_INTEGER
    const bPriority = priority.has(b.bot_id) ? priority.get(b.bot_id) : Number.MAX_SAFE_INTEGER
    if (aPriority !== bPriority) return aPriority - bPriority
    return a.bot_id.localeCompare(b.bot_id)
  })
})

const featuredBots = computed(() => orderedBots.value.filter((bot) => featuredBotIds.includes(bot.bot_id)))

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
  <div class="marketplace-page">
    <section class="hero-card">
      <div class="hero-copy">
        <div class="hero-kicker">Commercial Agent Desk</div>
        <h1>找达人</h1>
      </div>
    </section>

    <div
      v-loading="loading"
      class="agent-grid"
    >
      <article
        v-for="bot in featuredBots"
        :key="bot.bot_id"
        class="agent-card"
        @click="handleOrder(bot.bot_id)"
      >
        <div class="agent-card__glow" />
        <div v-if="bot.avatar_path" class="avatar-relief">
          <img :src="`/api/bots/${bot.bot_id}/avatar`" class="avatar-relief__base" alt="" />
        </div>

        <div class="agent-card__topline">
          <span class="agent-badge">{{ featuredBotIds.includes(bot.bot_id) ? '主推' : '隐藏' }}</span>
          <span class="agent-id">{{ bot.bot_id }}</span>
        </div>

        <div class="agent-card__head">
          <el-avatar :size="60" :src="bot.avatar_path ? `/api/bots/${bot.bot_id}/avatar` : undefined" class="agent-avatar">
            {{ bot.display_name[0] }}
          </el-avatar>
          <div class="agent-meta">
            <div class="agent-name">{{ bot.display_name }}</div>
            <div class="agent-subtitle">{{ bot.style_summary || bot.description?.slice(0, 36) || '暂无介绍' }}</div>
          </div>
        </div>

        <p class="agent-description">
          {{ bot.description || '暂无介绍' }}
        </p>

        <div class="agent-card__footer">
          <span class="agent-action-hint">点击进入下单</span>
          <el-button type="warning" class="agent-action" @click.stop="handleOrder(bot.bot_id)">下单</el-button>
        </div>
      </article>
    </div>

    <el-empty v-if="!loading && featuredBots.length === 0" description="暂无可接单的达人" />
  </div>
</template>

<style scoped>
.marketplace-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 8px 0 40px;
}

.hero-card {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  align-items: flex-end;
  margin-bottom: 28px;
  padding: 26px 28px;
  border-radius: 22px;
  background:
    radial-gradient(circle at top right, rgba(255, 214, 90, 0.22), transparent 28%),
    linear-gradient(135deg, #111523 0%, #1a2034 60%, #171b2b 100%);
  border: 1px solid rgba(216, 188, 110, 0.3);
  box-shadow: 0 20px 50px rgba(8, 13, 28, 0.22);
  color: #eef2ff;
}

.hero-kicker {
  font-size: 12px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: #f7c75c;
  margin-bottom: 10px;
}

.hero-copy h1 {
  margin: 0 0 8px;
  font-size: 34px;
  line-height: 1.05;
  color: #f5f7ff;
}

.hero-copy p {
  margin: 0;
  max-width: 560px;
  color: rgba(232, 236, 250, 0.72);
  line-height: 1.7;
}

.agent-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 18px;
}

.agent-card {
  position: relative;
  overflow: hidden;
  min-height: 290px;
  padding: 16px;
  border-radius: 18px;
  background: linear-gradient(145deg, #171c2c 0%, #101523 100%);
  border: 1px solid rgba(112, 127, 166, 0.28);
  box-shadow: 0 18px 36px rgba(8, 13, 28, 0.18);
  color: #eef2ff;
  cursor: pointer;
  transition: transform 0.24s ease, box-shadow 0.24s ease, border-color 0.24s ease;
}

.agent-card:hover {
  transform: translateY(-4px);
  border-color: rgba(247, 199, 92, 0.5);
  box-shadow: 0 22px 44px rgba(8, 13, 28, 0.28);
}

.agent-card__glow {
  position: absolute;
  inset: auto -20% -35% auto;
  width: 180px;
  height: 180px;
  border-radius: 999px;
  background: radial-gradient(circle, rgba(104, 229, 174, 0.24), transparent 68%);
  pointer-events: none;
}

.avatar-relief {
  position: absolute;
  right: -16px;
  bottom: -18px;
  width: 72%;
  height: 76%;
  opacity: 0.22;
  pointer-events: none;
  mask-image: radial-gradient(circle at 70% 70%, black 24%, transparent 70%);
  -webkit-mask-image: radial-gradient(circle at 70% 70%, black 24%, transparent 70%);
}

.avatar-relief__base {
  width: 100%;
  height: 100%;
  object-fit: cover;
  filter: grayscale(1) contrast(1.3) brightness(1.2);
}

.agent-card__topline {
  position: relative;
  z-index: 1;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 18px;
  font-size: 12px;
}

.agent-badge {
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(247, 199, 92, 0.14);
  color: #f7d27b;
  border: 1px solid rgba(247, 199, 92, 0.24);
}

.agent-id {
  color: rgba(223, 229, 250, 0.54);
  letter-spacing: 0.04em;
}

.agent-card__head {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 14px;
}

.agent-avatar {
  border: 1px solid rgba(247, 199, 92, 0.3);
  box-shadow: 0 10px 24px rgba(0, 0, 0, 0.22);
  flex-shrink: 0;
}

.agent-name {
  font-size: 22px;
  line-height: 1.1;
  font-weight: 600;
  color: #7de6b3;
}

.agent-subtitle {
  margin-top: 6px;
  font-size: 12px;
  line-height: 1.5;
  color: rgba(223, 229, 250, 0.62);
}

.agent-description {
  position: relative;
  z-index: 1;
  min-height: 66px;
  margin: 0 0 16px;
  color: rgba(236, 241, 255, 0.8);
  font-size: 14px;
  line-height: 1.65;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.agent-tags {
  position: relative;
  z-index: 1;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 18px;
}

.agent-tag {
  padding: 4px 9px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(130, 147, 188, 0.18);
  color: rgba(233, 238, 251, 0.82);
  font-size: 12px;
}

.agent-card__footer {
  position: relative;
  z-index: 1;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: auto;
}

.agent-action-hint {
  color: rgba(223, 229, 250, 0.48);
  font-size: 12px;
}

.agent-action {
  --el-button-bg-color: #f0a534;
  --el-button-border-color: #f0a534;
  --el-button-hover-bg-color: #f5b14f;
  --el-button-hover-border-color: #f5b14f;
  --el-button-active-bg-color: #db952e;
  --el-button-active-border-color: #db952e;
  font-weight: 600;
}

@media (max-width: 768px) {
  .hero-card {
    flex-direction: column;
    align-items: stretch;
    padding: 22px 20px;
  }

  .hero-copy h1 {
    font-size: 28px;
  }

  .agent-grid {
    grid-template-columns: 1fr;
  }
}
</style>
