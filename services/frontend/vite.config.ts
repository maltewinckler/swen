import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { TanStackRouterVite } from '@tanstack/router-plugin/vite'
import path from 'path'

// Parse allowed hosts from environment variable
// Format: comma-separated list (e.g., "swen.example.com,www.swen.example.com")
const allowedHosts = process.env.VITE_ALLOWED_HOSTS
  ? process.env.VITE_ALLOWED_HOSTS.split(',').map((host) => host.trim()).filter(Boolean)
  : []

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    TanStackRouterVite(),
    react(),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        // 6 minute timeout for long-running operations (bank sync can take 5 min)
        timeout: 360000,
      },
    },
  },
  preview: {
    port: 3000,
    host: '0.0.0.0',
    ...(allowedHosts.length > 0 && {
      allowedHosts,
    }),
  },
})
