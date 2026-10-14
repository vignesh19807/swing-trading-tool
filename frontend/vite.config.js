import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 3000,
    // Proxy configuration — uncomment and set target once backend port is confirmed.
    // This avoids CORS issues during local development.
    //
    // proxy: {
    //   '/api': {
    //     target: process.env.VITE_API_BASE_URL || 'http://localhost:5000',
    //     changeOrigin: true,
    //   },
    // },
  },
})
