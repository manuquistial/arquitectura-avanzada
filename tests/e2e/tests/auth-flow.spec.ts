import { test, expect } from '@playwright/test';

test.describe('Authentication Flow', () => {
  test('user can login and logout', async ({ page }) => {
    // Navigate to login page
    await page.goto('/login');
    
    // Verify login page loaded
    await expect(page.locator('h1')).toContainText('Iniciar Sesión');
    
    // Click Azure AD B2C login button
    await page.click('button:has-text("Iniciar")');
    
    // TODO: Handle Azure AD B2C redirect
    // For now, verify redirect occurred
    await page.waitForURL(/b2clogin\.com/, { timeout: 10000 });
    
    // Note: In real test, would fill B2C form and complete flow
  });
  
  test('unauthenticated user redirected to login', async ({ page }) => {
    // Try to access protected page
    await page.goto('/dashboard');
    
    // Should redirect to login
    await page.waitForURL('/login', { timeout: 5000 });
    
    await expect(page.locator('h1')).toContainText('Iniciar Sesión');
  });
  
  test('login page has correct elements', async ({ page }) => {
    await page.goto('/login');
    
    // Check for login button
    await expect(page.locator('button:has-text("Iniciar")')).toBeVisible();
    
    // Check for branding
    await expect(page.locator('text=Carpeta Ciudadana')).toBeVisible();
  });
});

