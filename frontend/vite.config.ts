import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

const API_BASE = process.env.VITE_API_BASE_URL || 'https://builddesk-api-149130710868.us-central1.run.app'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  server: {
    // Proxy /api/* to the backend — avoids CORS issues in local development
    proxy: {
      '/api': {
        target: API_BASE,
        changeOrigin: true,
        secure: true,
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: [],
    exclude: ['**/node_modules/**', '**/dist/**', 'e2e/**'],
  },
})
