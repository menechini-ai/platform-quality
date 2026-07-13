import { test, expect } from '@playwright/test';

const card = 'div.glass.rounded-xl.p-4.cursor-pointer';
const search = 'input[placeholder="Search by title or service..."]';

test.describe('Incidents — filtros', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/incidents');
    await page.waitForSelector(card);
  });

  test('lista incidentes (auto-sync)', async ({ page }) => {
    const rows = page.locator(card);
    await expect(rows.first()).toBeVisible();
    expect(await rows.count()).toBeGreaterThan(0);
  });

  test('busca por título restringe resultados', async ({ page }) => {
    const total = await page.locator(card).count();
    const title = (await page.locator(card).first().locator('h3').innerText()).trim();
    await page.locator(search).fill(title);
    await page.waitForTimeout(800);

    const filtered = await page.locator(card).count();
    expect(filtered).toBeGreaterThan(0);
    expect(filtered).toBeLessThanOrEqual(total);
    await expect(page.locator(card).first()).toContainText(title);
  });

  test('filtro de severidade (SEV-1)', async ({ page }) => {
    await page.getByRole('button', { name: 'SEV-1' }).click();
    await page.waitForTimeout(500);
    const cards = page.locator(card);
    const n = await cards.count();
    for (let i = 0; i < n; i++) {
      await expect(cards.nth(i)).toContainText('SEV-1');
    }
  });

  test('filtro de status (active)', async ({ page }) => {
    await page.getByRole('button', { name: 'active' }).click();
    await page.waitForTimeout(500);
    const cards = page.locator(card);
    const n = await cards.count();
    for (let i = 0; i < n; i++) {
      await expect(cards.nth(i)).toContainText('active');
    }
  });
});
