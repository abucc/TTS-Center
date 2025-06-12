import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 3003,
    proxy: {
      '/voices': {
        target: 'http://tts-gateway:9000',
        changeOrigin: true
      },
      '/tts': {
        target: 'http://tts-gateway:9000',
        changeOrigin: true
      },
      '/status': {
        target: 'http://tts-gateway:9000',
        changeOrigin: true
      },
      '/audio': {
        target: 'http://tts-gateway:9000',
        changeOrigin: true
      },
      '/play': {
        target: 'http://tts-gateway:9000',
        changeOrigin: true
      }
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: true
  }
})
