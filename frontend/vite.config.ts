import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      onwarn(warning, defaultHandler) {
        const normalizedId = warning.id?.replaceAll('\\', '/') ?? ''
        const isKnownZodAnnotation =
          warning.code === 'INVALID_ANNOTATION' &&
          warning.message.includes('contains an annotation that Rollup cannot interpret') &&
          (normalizedId.endsWith('/node_modules/zod/v4/core/regexes.js') ||
            normalizedId.endsWith('/node_modules/zod/v4/core/util.js'))

        // These two Zod source comments mention @__PURE__ descriptively; Rollup removes them.
        if (isKnownZodAnnotation) return
        defaultHandler(warning)
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
