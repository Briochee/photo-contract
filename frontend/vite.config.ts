import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: {
    rolldownOptions: {
      onLog(level, warning, defaultHandler) {
        const normalizedId = warning.id?.replaceAll('\\', '/') ?? ''
        const isKnownZodAnnotation =
          level === 'warn' &&
          warning.code === 'INVALID_ANNOTATION' &&
          (normalizedId.endsWith('/node_modules/zod/v4/core/regexes.js') ||
            normalizedId.endsWith('/node_modules/zod/v4/core/util.js'))

        // These Zod comments describe annotation placement; removing them does not change output.
        if (isKnownZodAnnotation) return
        defaultHandler(level, warning)
      },
    },
  },
  server: {
    host: '127.0.0.1',
    strictPort: true,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/health': { target: 'http://127.0.0.1:8000', changeOrigin: true },
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: './src/test-setup.ts',
    css: true,
  },
})
