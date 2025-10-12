import { test, expect } from '@playwright/test';

// Helper to login
async function loginAsUser(page: any, userId: string = 'user-1') {
  await page.goto('/');
  await page.evaluate((id) => {
    sessionStorage.setItem('user', JSON.stringify({
      id: id,
      email: `${id}@example.com`,
      name: `Test User ${id}`,
      roles: ['user']
    }));
  }, userId);
}

test.describe('Document Transfer Flow', () => {
  test('user can view transfers page', async ({ page }) => {
    await loginAsUser(page);
    await page.goto('/transfers');
    
    await expect(page.locator('h1')).toContainText('Transferencias');
  });
  
  test('user can initiate transfer', async ({ page }) => {
    await loginAsUser(page, 'sender-123');
    
    // Go to documents
    await page.goto('/documents');
    
    // Select document
    await page.click('[data-testid="document-row"]:first-child');
    
    // Click transfer button
    await page.click('button:has-text("Transferir")');
    
    // Fill transfer form
    await page.fill('input[name="recipient_email"]', 'recipient@example.com');
    await page.fill('textarea[name="message"]', 'Aquí está el documento');
    
    // Submit transfer
    await page.click('button:has-text("Enviar Transferencia")');
    
    // Verify success
    await expect(page.locator('text=Transferencia iniciada')).toBeVisible({ timeout: 10000 });
  });
  
  test('recipient can see pending transfer', async ({ page }) => {
    await loginAsUser(page, 'recipient-456');
    
    await page.goto('/transfers');
    
    // Should see incoming transfers
    await expect(page.locator('text=Recibidas')).toBeVisible();
    
    // Check for pending transfer
    const pendingTransfer = page.locator('[data-testid="transfer-pending"]');
    await expect(pendingTransfer.first()).toBeVisible();
  });
  
  test('recipient can accept transfer', async ({ page }) => {
    await loginAsUser(page, 'recipient-456');
    
    await page.goto('/transfers');
    
    // Click on first pending transfer
    const firstTransfer = page.locator('[data-testid="transfer-pending"]').first();
    await firstTransfer.click();
    
    // Click accept button
    await page.click('button:has-text("Aceptar")');
    
    // Confirm
    await page.click('button:has-text("Confirmar")');
    
    // Verify success
    await expect(page.locator('text=Transferencia aceptada')).toBeVisible({ timeout: 10000 });
  });
  
  test('recipient can reject transfer', async ({ page }) => {
    await loginAsUser(page, 'recipient-456');
    
    await page.goto('/transfers');
    
    // Click on first pending transfer
    const firstTransfer = page.locator('[data-testid="transfer-pending"]').first();
    await firstTransfer.click();
    
    // Click reject button
    await page.click('button:has-text("Rechazar")');
    
    // Fill rejection reason
    await page.fill('textarea[name="reason"]', 'No es para mí');
    
    // Confirm
    await page.click('button:has-text("Confirmar Rechazo")');
    
    // Verify success
    await expect(page.locator('text=Transferencia rechazada')).toBeVisible({ timeout: 10000 });
  });
  
  test('sender can cancel pending transfer', async ({ page }) => {
    await loginAsUser(page, 'sender-123');
    
    await page.goto('/transfers');
    
    // Switch to sent transfers
    await page.click('text=Enviadas');
    
    // Click on first pending transfer
    const firstTransfer = page.locator('[data-testid="transfer-pending"]').first();
    await firstTransfer.click();
    
    // Click cancel button
    await page.click('button:has-text("Cancelar")');
    
    // Confirm
    await page.click('button:has-text("Confirmar Cancelación")');
    
    // Verify success
    await expect(page.locator('text=Transferencia cancelada')).toBeVisible({ timeout: 10000 });
  });
  
  test('completed transfer shows in history', async ({ page }) => {
    await loginAsUser(page);
    
    await page.goto('/transfers');
    
    // Click history tab
    await page.click('text=Historial');
    
    // Should see completed transfers
    const completedTransfers = page.locator('[data-testid="transfer-completed"]');
    await expect(completedTransfers.count()).resolves.toBeGreaterThan(0);
  });
});

