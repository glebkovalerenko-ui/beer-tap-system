// ПРАВИЛЬНЫЙ ВАРИАНТ (Svelte + Vite)
import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [svelte()],
  // --- ДОБАВЛЕНО: Явные настройки сервера ---
  server: {
    port: 5173,
    strictPort: true, // Если порт занят, не переходить на другой, а падать с ошибкой
    host: true,       // Слушать на всех адресах (помогает на Windows)
  }
})