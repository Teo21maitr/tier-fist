import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Adresse du backend Django en développement. On vise 127.0.0.1 plutôt que
// « localhost » : ce dernier peut résoudre en IPv6 (::1) et atteindre un autre
// service qui écouterait sur le même port. Surchargeable via VITE_API_TARGET.
const apiTarget = process.env.VITE_API_TARGET ?? 'http://127.0.0.1:8000'

export default defineConfig(({ command }) => ({
  plugins: [react()],

  // En production, Django sert le build : les assets sont exposés sous /static/
  // par WhiteNoise, et index.html doit donc les référencer avec ce préfixe.
  // En développement, Vite sert l'application à la racine.
  base: command === 'build' ? '/static/' : '/',

  // En développement, Vite proxifie l'API vers Django : le frontend et le backend
  // partagent la même origine, les cookies de session fonctionnent sans CORS.
  server: {
    // Adresse explicite : évite les surprises IPv4/IPv6 côté proxy et E2E.
    host: '127.0.0.1',
    port: 5173,
    proxy: {
      '/api': { target: apiTarget, changeOrigin: true },
      '/media': { target: apiTarget, changeOrigin: true },
      '/admin': { target: apiTarget, changeOrigin: true },
    },
  },

  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
}))
