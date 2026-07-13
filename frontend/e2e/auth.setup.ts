import { test as setup } from '@playwright/test';

const authFile = './e2e/.auth/user.json';

setup('authenticate', async ({ page }) => {
  await page.goto('/login');
  await page.locator('input').first().fill('admin');
  await page.locator('input[type="password"]').fill('admin');
  await page.getByRole('button', { name: 'Sign in' }).click();
  await page.waitForFunction(() => localStorage.getItem('observai_token'));
  await page.context().storageState({ path: authFile });
});
