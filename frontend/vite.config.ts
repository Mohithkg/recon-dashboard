import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/health': 'http://localhost:8000',
      '/auth': 'http://localhost:8000',
      '/uploads': 'http://localhost:8000',
      '/reconcile': 'http://localhost:8000',
      '/dashboard': 'http://localhost:8000',
    },
  },
})
