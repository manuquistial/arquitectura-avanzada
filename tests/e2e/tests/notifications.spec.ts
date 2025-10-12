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

test.describe('Notifications', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsUser(page);
  });
  
  test('user can view notifications page', async ({ page }) => {
    await page.goto('/notifications');
    
    await expect(page.locator('h1')).toContainText('Notificaciones');
  });
  
  test('user can filter notifications', async ({ page }) => {
    await page.goto('/notifications');
    
    // Click "No leídas" filter
    await page.click('button:has-text("No leídas")');
    
    // Button should be active
    await expect(page.locator('button:has-text("No leídas")')).toHaveClass(/bg-blue-600/);
    
    // Switch to "Todas"
    await page.click('button:has-text("Todas")');
    
    await expect(page.locator('button:has-text("Todas")')).toHaveClass(/bg-blue-600/);
  });
  
  test('user can mark notification as read', async ({ page }) => {
    await page.goto('/notifications');
    
    // Find first unread notification
    const unreadNotification = page.locator('[data-testid="notification-unread"]').first();
    
    if (await unreadNotification.count() > 0) {
      // Click mark as read button
      await unreadNotification.locator('button[title="Marcar como leída"]').click();
      
      // Should update to read state
      await expect(unreadNotification).not.toBeVisible();
    }
  });
  
  test('user can mark all as read', async ({ page }) => {
    await page.goto('/notifications');
    
    // Click mark all as read
    await page.click('button:has-text("Marcar todas como leídas")');
    
    // All notifications should be marked as read
    await expect(page.locator('[data-testid="notification-unread"]')).toHaveCount(0);
  });
  
  test('user can delete notification', async ({ page }) => {
    await page.goto('/notifications');
    
    // Count notifications before
    const countBefore = await page.locator('[data-testid="notification-item"]').count();
    
    if (countBefore > 0) {
      // Delete first notification
      await page.click('[data-testid="notification-item"]:first-child button:has-text("🗑️")');
      
      // Should be removed
      const countAfter = await page.locator('[data-testid="notification-item"]').count();
      expect(countAfter).toBeLessThan(countBefore);
    }
  });
  
  test('notification links navigate correctly', async ({ page }) => {
    await page.goto('/notifications');
    
    // Click on notification with link
    const notificationWithLink = page.locator('[data-testid="notification-item"]:has(button:has-text("Ver detalles"))').first();
    
    if (await notificationWithLink.count() > 0) {
      await notificationWithLink.locator('button:has-text("Ver detalles")').click();
      
      // Should navigate to linked page
      await expect(page.url()).toMatch(/\/(documents|transfers)/);
    }
  });
  
  test('empty notifications shows placeholder', async ({ page }) => {
    await page.goto('/notifications');
    
    // If no notifications, should show empty state
    const notifications = page.locator('[data-testid="notification-item"]');
    const count = await notifications.count();
    
    if (count === 0) {
      await expect(page.locator('text=No hay notificaciones')).toBeVisible();
      await expect(page.locator('text=📭')).toBeVisible();
    }
  });
});

