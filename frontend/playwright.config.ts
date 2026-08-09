import { defineConfig, devices } from '@playwright/test'

/**
 * Tests E2E Tier Fist.
 *
 * Prérequis : le backend Django doit tourner (par défaut sur 127.0.0.1:8000)
 * avec le jeu de démonstration chargé :
 *
 *   cd backend && .venv/bin/python manage.py seed_demo --reset
 *   cd backend && .venv/bin/python manage.py runserver
 *
 * Playwright démarre lui-même le serveur Vite.
 */
export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? 'list' : [['list']],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? 'http://127.0.0.1:5173',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'] } },
    { name: 'mobile', use: { ...devices['Pixel 5'] } },
  ],
  webServer: {
    command: 'npm run dev',
    url: 'http://127.0.0.1:5173',
    reuseExistingServer: true,
    timeout: 60_000,
  },
})
