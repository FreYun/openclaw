import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useConsultStore = defineStore('consult', () => {
  const result = ref(null)
  const originalMessage = ref('')

  function setResult(r, message) {
    result.value = r
    originalMessage.value = message || ''
  }

  function clear() {
    result.value = null
    originalMessage.value = ''
  }

  return { result, originalMessage, setResult, clear }
})
