import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  use: { baseURL: 'http://localhost:5174' },
  webServer: [
    {
      command: 'uv run python manage.py runserver 8001 --noreload',
      cwd: '../backend',
      port: 8001,
      reuseExistingServer: true,
    },
    {
      command: 'npx vite --port 5174 --strictPort',
      env: { API_PROXY: 'http://localhost:8001' },
      port: 5174,
      reuseExistingServer: true,
    },
  ],
})
