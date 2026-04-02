import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 18901,
    proxy: {
      '/api': 'http://localhost:18900',
    },
  },
})
