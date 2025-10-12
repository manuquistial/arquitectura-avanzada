import { test, expect } from '@playwright/test';

async function loginAsUser(page: any) {
  await page.goto('/');
  await page.evaluate(() => {
    sessionStorage.setItem('user', JSON.stringify({
      id: 'user-123',
      email: 'test@example.com',
      name: 'Test User',
      roles: ['user']
    }));
  });
}

test.describe('Document Sharing Flow', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsUser(page);
  });
  
  test('user can create shortlink', async ({ page }) => {
    await page.goto('/documents');
    
    // Select document
    await page.click('[data-testid="document-row"]:first-child');
    
    // Click share button
    await page.click('button:has-text("Compartir")');
    
    // Configure shortlink
    await page.fill('input[name="max_views"]', '10');
    await page.fill('input[name="expires_hours"]', '24');
    
    // Generate shortlink
    await page.click('button:has-text("Generar Link")');
    
    // Verify shortlink created
    await expect(page.locator('[data-testid="shortlink-url"]')).toBeVisible({ timeout: 10000 });
    
    // Copy button should be visible
    await expect(page.locator('button:has-text("Copiar")')).toBeVisible();
  });
  
  test('user can copy shortlink to clipboard', async ({ page, context }) => {
    await page.goto('/documents');
    
    // Assume shortlink exists
    await page.click('[data-testid="document-row"]:first-child');
    await page.click('button:has-text("Compartir")');
    await page.click('button:has-text("Generar Link")');
    
    // Grant clipboard permissions
    await context.grantPermissions(['clipboard-read', 'clipboard-write']);
    
    // Click copy button
    await page.click('button:has-text("Copiar")');
    
    // Verify success message
    await expect(page.locator('text=Copiado')).toBeVisible();
  });
  
  test('anonymous user can access valid shortlink', async ({ page }) => {
    // Don't login - anonymous access
    
    // Navigate to shortlink (example code)
    await page.goto('/s/abc123xyz');
    
    // Should see document or download page
    await expect(page.locator('h1, h2, h3')).toContainText(/Documento|Descargar/);
    
    // Download button should be visible
    await expect(page.locator('button:has-text("Descargar")')).toBeVisible();
  });
  
  test('expired shortlink shows error', async ({ page }) => {
    // Navigate to expired shortlink
    await page.goto('/s/expired_code');
    
    // Should show error
    await expect(page.locator('text=expirado|no encontrado|no válido')).toBeVisible();
    
    // Should have 404 or error page
    await expect(page.locator('text=404|Error')).toBeVisible();
  });
  
  test('shortlink tracks views', async ({ page }) => {
    await loginAsUser(page);
    await page.goto('/documents');
    
    // View document shortlinks
    await page.click('[data-testid="document-row"]:first-child');
    await page.click('text=Enlaces');
    
    // Should show views count
    await expect(page.locator('text=Vistas:')).toBeVisible();
    
    // Should show remaining views
    await expect(page.locator('text=Restantes:')).toBeVisible();
  });
  
  test('user can revoke shortlink', async ({ page }) => {
    await loginAsUser(page);
    await page.goto('/documents');
    
    // Select document with shortlinks
    await page.click('[data-testid="document-row"]:first-child');
    await page.click('text=Enlaces');
    
    // Click revoke on first shortlink
    await page.click('[data-testid="shortlink-item"]:first-child button:has-text("Revocar")');
    
    // Confirm
    await page.click('button:has-text("Confirmar")');
    
    // Verify revoked
    await expect(page.locator('text=Link revocado')).toBeVisible();
  });
  
  test('shortlink configuration validates input', async ({ page }) => {
    await loginAsUser(page);
    await page.goto('/documents');
    
    await page.click('[data-testid="document-row"]:first-child');
    await page.click('button:has-text("Compartir")');
    
    // Try invalid values
    await page.fill('input[name="max_views"]', '-1');
    await page.click('button:has-text("Generar Link")');
    
    // Should show validation error
    await expect(page.locator('text=valor válido|positivo')).toBeVisible();
  });
});

