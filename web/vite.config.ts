import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

const api = process.env.FV_API ?? 'http://localhost:8000'
// VITE_STATIC=1 builds one self-contained page (fonts inlined, a single bundle) for hosting without the server
const page = process.env.VITE_STATIC === '1'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: page
    ? {
        outDir: 'dist/page',
        emptyOutDir: true,
        assetsInlineLimit: 4_000_000,
        cssCodeSplit: false,
        chunkSizeWarningLimit: 4000,
        rollupOptions: { output: { inlineDynamicImports: true } },
      }
    : {
        outDir: '../falconverifier/static',
        emptyOutDir: true,
        chunkSizeWarningLimit: 900,
      },
  server: {
    proxy: {
      '/api': { target: api, changeOrigin: true },
      '/healthz': { target: api, changeOrigin: true },
    },
  },
})
