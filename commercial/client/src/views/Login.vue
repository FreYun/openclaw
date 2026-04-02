<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../store/auth.js'
import { ElMessage } from 'element-plus'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const isRegister = ref(false)
const loading = ref(false)
const form = ref({
  username: '',
  password: '',
  display_name: '',
  company: '',
})

async function handleSubmit() {
  loading.value = true
  try {
    if (isRegister.value) {
      await auth.register(form.value)
      ElMessage.success('注册成功')
    } else {
      await auth.login(form.value.username, form.value.password)
      ElMessage.success('登录成功')
    }
    router.push(route.query.redirect || '/')
  } catch (err) {
    ElMessage.error(err.response?.data?.error || '操作失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div style="display: flex; justify-content: center; align-items: center; min-height: 60vh">
    <el-card style="width: 400px">
      <template #header>
        <div style="text-align: center; font-size: 18px; font-weight: bold">
          {{ isRegister ? '注册账号' : '登录' }}
        </div>
      </template>

      <el-form @submit.prevent="handleSubmit" label-position="top">
        <el-form-item label="用户名">
          <el-input v-model="form.username" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" placeholder="请输入密码" show-password />
        </el-form-item>
        <template v-if="isRegister">
          <el-form-item label="昵称">
            <el-input v-model="form.display_name" placeholder="您的昵称" />
          </el-form-item>
          <el-form-item label="公司（选填）">
            <el-input v-model="form.company" placeholder="公司名称" />
          </el-form-item>
        </template>
        <el-form-item>
          <el-button type="primary" native-type="submit" :loading="loading" style="width: 100%">
            {{ isRegister ? '注册' : '登录' }}
          </el-button>
        </el-form-item>
      </el-form>

      <div style="text-align: center">
        <el-button text @click="isRegister = !isRegister">
          {{ isRegister ? '已有账号？去登录' : '没有账号？去注册' }}
        </el-button>
      </div>
    </el-card>
  </div>
</template>
