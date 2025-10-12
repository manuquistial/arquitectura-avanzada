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

test.describe('Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsUser(page);
  });
  
  test('dashboard loads with stats', async ({ page }) => {
    await page.goto('/dashboard');
    
    await expect(page.locator('h1')).toContainText('Dashboard');
    
    // Check for stats cards
    await expect(page.locator('text=Total Documentos')).toBeVisible();
    await expect(page.locator('text=Firmados')).toBeVisible();
    await expect(page.locator('text=Transferencias')).toBeVisible();
    await expect(page.locator('text=Compartidos')).toBeVisible();
  });
  
  test('activity timeline shows recent activities', async ({ page }) => {
    await page.goto('/dashboard');
    
    // Check for activity timeline
    await expect(page.locator('text=Actividad Reciente')).toBeVisible();
    
    // Should have time filter buttons
    await expect(page.locator('button:has-text("Hoy")')).toBeVisible();
    await expect(page.locator('button:has-text("Semana")')).toBeVisible();
  });
  
  test('user can filter activity by time', async ({ page }) => {
    await page.goto('/dashboard');
    
    // Click "Hoy" filter
    await page.click('button:has-text("Hoy")');
    
    // Button should be active
    await expect(page.locator('button:has-text("Hoy")')).toHaveClass(/bg-blue-600/);
    
    // Switch to "Mes"
    await page.click('button:has-text("Mes")');
    
    await expect(page.locator('button:has-text("Mes")')).toHaveClass(/bg-blue-600/);
  });
  
  test('quick actions navigate correctly', async ({ page }) => {
    await page.goto('/dashboard');
    
    // Click "Subir Documento" quick action
    await page.click('text=Subir Documento');
    
    // Should navigate to documents page
    await expect(page.url()).toContain('/documents');
  });
  
  test('stats are displayed with correct format', async ({ page }) => {
    await page.goto('/dashboard');
    
    // Stats should be numbers
    const totalDocs = page.locator('text=Total Documentos').locator('..').locator('[class*="text-"]');
    await expect(totalDocs.first()).toBeVisible();
    
    // Check format (should be a number)
    const text = await totalDocs.first().textContent();
    expect(text).toMatch(/^\d+$/);
  });
});

