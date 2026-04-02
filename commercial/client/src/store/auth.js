import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api/index.js'

export const useAuthStore = defineStore('auth', () => {
  const client = ref(null)
  const token = ref(localStorage.getItem('token') || '')
  const isLoggedIn = computed(() => !!token.value)

  async function login(username, password) {
    const { data } = await api.post('/auth/login', { username, password })
    token.value = data.token
    client.value = data.client
    localStorage.setItem('token', data.token)
    return data
  }

  async function register(form) {
    const { data } = await api.post('/auth/register', form)
    token.value = data.token
    client.value = data.client
    localStorage.setItem('token', data.token)
    return data
  }

  async function fetchMe() {
    if (!token.value) return
    try {
      const { data } = await api.get('/auth/me')
      client.value = data
    } catch {
      logout()
    }
  }

  function logout() {
    token.value = ''
    client.value = null
    localStorage.removeItem('token')
  }

  return { client, token, isLoggedIn, login, register, fetchMe, logout }
})
