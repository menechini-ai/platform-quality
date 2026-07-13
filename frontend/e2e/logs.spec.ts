import { test, expect } from '@playwright/test';

const row = 'div.glass.rounded-lg.p-3';
const queryInput = 'input[placeholder="service:api status:error"]';
const tagsInput = 'input[placeholder="Tags (e.g. env:prod)"]';
const searchBtn = 'button:has-text("Search")';

async function search(page: import('@playwright/test').Page, query: string, tags = '') {
  await page.locator(queryInput).fill(query);
  if (tags) await page.locator(tagsInput).fill(tags);
  await page.locator(searchBtn).click();
  await page.waitForTimeout(1500);
}

test.describe('Logs — filtros', () => {
  test('não lista sem busca (sem match-all padrão)', async ({ page }) => {
    await page.goto('/logs');
    await expect(page.getByText('Enter a query and click Search')).toBeVisible();
    expect(await page.locator(row).count()).toBe(0);
  });

  test('query status:error retorna logs', async ({ page }) => {
    await page.goto('/logs');
    await search(page, 'status:error');
    expect(await page.locator(row).count()).toBeGreaterThan(0);
  });

  test('filtro de tag existente (service:agent) aplica', async ({ page }) => {
    await page.goto('/logs');
    await search(page, 'status:error', 'service:agent');
    const n = await page.locator(row).count();
    expect(n).toBeGreaterThan(0);
  });

  test('filtro de tag inexistente (env:prod) restringe a vazio', async ({ page }) => {
    await page.goto('/logs');
    await search(page, 'status:error', 'env:prod');
    expect(await page.locator(row).count()).toBe(0);
    await expect(page.getByText('No logs match')).toBeVisible();
  });
});
