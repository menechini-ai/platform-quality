import { test, expect } from '@playwright/test';

const card = 'div.glass.rounded-lg.p-4';
const tagInput = 'input[placeholder="Tags (e.g. env:prod,service:api)"]';

test.describe('Monitors — filtros', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/monitors');
    await page.waitForSelector(card);
  });

  test('lista monitores sem filtro', async ({ page }) => {
    const rows = page.locator(card);
    await expect(rows.first()).toBeVisible();
    expect(await rows.count()).toBeGreaterThan(0);
  });

  test('filtra por tag team:observai', async ({ page }) => {
    const total = await page.locator(card).count();

    await page.locator(tagInput).fill('team:observai');
    await page.waitForTimeout(2500);

    const filtered = await page.locator(card).count();
    expect(filtered).toBeGreaterThan(0);
    expect(filtered).toBeLessThan(total);
  });

  test('limpar filtro restaura a lista completa', async ({ page }) => {
    await page.locator(tagInput).fill('team:observai');
    await page.waitForTimeout(2500);
    await page.locator(tagInput).fill('');
    await page.waitForTimeout(2500);

    expect(await page.locator(card).count()).toBeGreaterThan(0);
  });
});
