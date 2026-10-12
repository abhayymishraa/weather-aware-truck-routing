import { expect, test } from '@playwright/test'

test('plans a trip and moves the forecast slider', async ({ page }) => {
  await page.goto('/')

  await page.getByRole('combobox', { name: 'Origin' }).fill('Dallas')
  await page.getByRole('option', { name: /Dallas, Texas/ }).first().click()
  await page.getByRole('combobox', { name: 'Destination' }).fill('Denver')
  await page.getByRole('option', { name: /Denver/ }).first().click()
  await page.getByRole('button', { name: 'Find safest route' }).click()

  await expect(page.getByText('Recommended')).toBeVisible({ timeout: 45_000 })
  await expect(page.getByText(/^Route [ABC]$/).first()).toBeVisible()

  const slider = page.getByRole('slider', { name: 'Forecast hour' })
  await slider.focus()
  await page.keyboard.press('End')
  await expect(page.getByText(/\(\+47 h\)/)).toBeVisible()
})
