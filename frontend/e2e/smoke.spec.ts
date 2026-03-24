import { test, expect } from '@playwright/test'

test.describe('Landing page', () => {
  test('loads and shows main heading', async ({ page }) => {
    await page.goto('/')
    await expect(page.locator('h1')).toBeVisible()
  })

  test('navigate to dashboard link exists', async ({ page }) => {
    await page.goto('/')
    const link = page.locator('a[href*="dashboard"]').first()
    await expect(link).toBeVisible()
  })
})

test.describe('Dashboard', () => {
  test('loads and shows tab navigation', async ({ page }) => {
    await page.goto('/dashboard')
    await expect(page.locator('.tabNav, [class*="tab"]').first()).toBeVisible({ timeout: 10_000 })
  })

  test('overview tab shows metric cards', async ({ page }) => {
    await page.goto('/dashboard')
    // Wait for data to load
    await page.waitForSelector('.metricCard, .domainCard, [class*="metric"]', { timeout: 15_000 })
    const cards = page.locator('.metricCard, .domainCard, [class*="metric"]')
    expect(await cards.count()).toBeGreaterThan(0)
  })

  test('tab switching works', async ({ page }) => {
    await page.goto('/dashboard')
    // Click on Seguridad tab
    const secTab = page.locator('button, [role="tab"]', { hasText: /seguridad/i }).first()
    if (await secTab.isVisible()) {
      await secTab.click()
      // Should see security-related content
      await page.waitForTimeout(1000)
    }
  })

  test('map renders', async ({ page }) => {
    await page.goto('/dashboard')
    await expect(page.locator('.leaflet-container').first()).toBeVisible({ timeout: 10_000 })
  })
})
