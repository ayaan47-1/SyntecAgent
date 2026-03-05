import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  if (mode === 'widget') {
    return {
      plugins: [react()],
      build: {
        outDir: 'dist-widget',
        lib: {
          entry: 'src/syntec-widget-entry.jsx',
          name: 'SyntecChatWidget',
          fileName: 'syntec-chat-widget',
          formats: ['iife']
        },
        rollupOptions: {
          output: { inlineDynamicImports: true }
        },
        cssCodeSplit: false
      }
    }
  }
  return {
    plugins: [react()],
    server: {
      port: 5177
    }
  }
})
