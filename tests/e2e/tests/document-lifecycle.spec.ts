import { test, expect } from '@playwright/test';

// Helper to login (mock for testing)
async function loginAsUser(page: any) {
  // In real scenario, would complete Azure AD B2C flow
  // For testing, we'll navigate directly after setting auth cookie/session
  
  // Mock authentication by setting session storage
  await page.goto('/');
  await page.evaluate(() => {
    sessionStorage.setItem('user', JSON.stringify({
      id: 'test-user-123',
      email: 'test@example.com',
      name: 'Test User',
      roles: ['user']
    }));
  });
}

test.describe('Document Lifecycle', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await loginAsUser(page);
  });
  
  test('user can view documents page', async ({ page }) => {
    await page.goto('/documents');
    
    // Check page loaded
    await expect(page.locator('h1')).toContainText('Mis Documentos');
    
    // Check for upload button
    await expect(page.locator('button:has-text("Subir")')).toBeVisible();
  });
  
  test('user can upload document', async ({ page }) => {
    await page.goto('/documents');
    
    // Click upload button
    await page.click('button:has-text("Subir")');
    
    // Fill upload form
    const fileInput = page.locator('input[type="file"]');
    
    // Create test file
    const buffer = Buffer.from('Test PDF content');
    await fileInput.setInputFiles({
      name: 'test-document.pdf',
      mimeType: 'application/pdf',
      buffer: buffer,
    });
    
    // Select document type
    await page.selectOption('select[name="document_type"]', 'cedula');
    
    // Submit
    await page.click('button:has-text("Cargar")');
    
    // Verify success message or redirect
    await expect(page.locator('text=test-document.pdf')).toBeVisible({ timeout: 10000 });
  });
  
  test('document appears in list after upload', async ({ page }) => {
    await page.goto('/documents');
    
    // Should see documents list
    await expect(page.locator('[data-testid="documents-list"]')).toBeVisible();
    
    // Check for at least one document row
    const documentRows = page.locator('[data-testid="document-row"]');
    await expect(documentRows.first()).toBeVisible();
  });
  
  test('user can view document details', async ({ page }) => {
    await page.goto('/documents');
    
    // Click first document
    await page.click('[data-testid="document-row"]:first-child');
    
    // Should show document details
    await expect(page.locator('text=Detalles del Documento')).toBeVisible();
    
    // Should have action buttons
    await expect(page.locator('button:has-text("Descargar")')).toBeVisible();
  });
  
  test('user can download document', async ({ page }) => {
    await page.goto('/documents');
    
    // Start waiting for download
    const downloadPromise = page.waitForEvent('download');
    
    // Click download on first document
    await page.click('[data-testid="document-row"]:first-child button:has-text("Descargar")');
    
    // Wait for download
    const download = await downloadPromise;
    
    // Verify download started
    expect(download.suggestedFilename()).toBeTruthy();
  });
  
  test('WORM-locked document cannot be deleted', async ({ page }) => {
    await page.goto('/documents');
    
    // Find WORM-locked document (if exists)
    const wormDocument = page.locator('[data-testid="document-row"]:has-text("🔒")');
    
    if (await wormDocument.count() > 0) {
      // Delete button should be disabled
      const deleteButton = wormDocument.locator('button:has-text("Eliminar")');
      await expect(deleteButton).toBeDisabled();
    }
  });
});

