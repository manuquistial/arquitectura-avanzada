import { test, expect, Page } from '@playwright/test';

/**
 * Complete E2E flow test for Carpeta Ciudadana
 * 
 * Flow:
 * 1. Register citizen
 * 2. Upload document
 * 3. Sign document
 * 4. Authenticate with MinTIC hub
 * 5. Search documents
 * 6. Share document
 * 7. Transfer to another operator
 * 8. Confirm transfer
 */

// Test data
const testCitizen = {
  identification: '1234567890',
  name: 'Juan Perez',
  email: 'juan.perez@example.com',
  phone: '3001234567',
  address: 'Calle 123 #45-67'
};

const testDocument = {
  title: 'Certificado de Estudios',
  description: 'Certificado universitario',
  file: 'test-document.pdf'
};

// Mock MinTIC Hub responses
test.beforeEach(async ({ page }) => {
  // Intercept MinTIC Hub calls and return mock responses
  await page.route('**/apis/registerCitizen', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        message: 'Ciudadano registrado exitosamente',
        citizen: testCitizen
      })
    });
  });
  
  await page.route('**/apis/authenticateDocument', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        success: true,
        message: 'Documento autenticado',
        documentId: 'doc-123',
        timestamp: new Date().toISOString()
      })
    });
  });
  
  await page.route('**/apis/getOperators', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        operators: [
          {
            id: 'operator-demo',
            name: 'Carpeta Ciudadana Demo',
            endpoint: 'http://localhost:8000'
          },
          {
            id: 'operator-test',
            name: 'Operador de Prueba',
            endpoint: 'http://localhost:8001'
          }
        ]
      })
    });
  });
});

test.describe('Complete User Flow', () => {
  test('should complete full workflow: register → upload → sign → search → share → transfer', async ({ page }) => {
    // Step 1: Register citizen
    test.step('Register citizen', async () => {
      await page.goto('/register');
      await expect(page).toHaveTitle(/Registro/i);
      
      await page.fill('input[name="identification"]', testCitizen.identification);
      await page.fill('input[name="name"]', testCitizen.name);
      await page.fill('input[name="email"]', testCitizen.email);
      await page.fill('input[name="phone"]', testCitizen.phone);
      await page.fill('input[name="address"]', testCitizen.address);
      
      await page.click('button[type="submit"]');
      
      // Wait for success message
      await expect(page.locator('text=/registrado exitosamente/i')).toBeVisible({ timeout: 10000 });
    });
    
    // Step 2: Login
    test.step('Login', async () => {
      await page.goto('/login');
      await page.fill('input[name="identification"]', testCitizen.identification);
      await page.click('button[type="submit"]');
      
      // Should redirect to dashboard
      await expect(page).toHaveURL(/\/dashboard/);
    });
    
    // Step 3: Upload document
    let documentId: string;
    
    test.step('Upload document', async () => {
      await page.goto('/upload');
      
      await page.fill('input[name="title"]', testDocument.title);
      await page.fill('textarea[name="description"]', testDocument.description);
      
      // Upload file
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles({
        name: testDocument.file,
        mimeType: 'application/pdf',
        buffer: Buffer.from('Mock PDF content')
      });
      
      await page.click('button[type="submit"]');
      
      // Wait for upload success
      await expect(page.locator('text=/subido exitosamente/i')).toBeVisible({ timeout: 15000 });
      
      // Extract document ID from URL or response
      documentId = await page.evaluate(() => {
        const url = new URL(window.location.href);
        return url.searchParams.get('documentId') || 'doc-123';
      });
    });
    
    // Step 4: Sign document
    test.step('Sign document', async () => {
      await page.goto(`/documents/${documentId}/sign`);
      
      await page.click('button:has-text("Firmar Documento")');
      
      // Wait for signature confirmation
      await expect(page.locator('text=/firmado exitosamente/i')).toBeVisible({ timeout: 10000 });
    });
    
    // Step 5: Authenticate with MinTIC hub
    test.step('Authenticate document with hub', async () => {
      await page.click('button:has-text("Autenticar con MinTIC")');
      
      // Wait for hub authentication
      await expect(page.locator('text=/autenticado.*hub/i')).toBeVisible({ timeout: 10000 });
    });
    
    // Step 6: Search documents
    test.step('Search documents', async () => {
      await page.goto('/search');
      
      await page.fill('input[name="query"]', testDocument.title);
      await page.click('button:has-text("Buscar")');
      
      // Should find the uploaded document
      await expect(page.locator(`text=${testDocument.title}`)).toBeVisible();
    });
    
    // Step 7: Share document
    let shareToken: string;
    
    test.step('Share document', async () => {
      await page.goto(`/documents/${documentId}`);
      
      await page.click('button:has-text("Compartir")');
      
      // Fill share form
      await page.fill('input[name="audience"]', 'public');
      await page.fill('input[name="expiresAt"]', '2025-12-31');
      
      await page.click('button:has-text("Generar Enlace")');
      
      // Extract share token
      const shareLink = await page.locator('[data-testid="share-link"]').textContent();
      shareToken = shareLink?.split('/s/')[1] || 'mock-token';
      
      await expect(page.locator('text=/enlace generado/i')).toBeVisible();
    });
    
    // Step 8: Access shared document (in new context)
    test.step('Access shared document', async () => {
      const newPage = await page.context().newPage();
      
      await newPage.goto(`/s/${shareToken}`);
      
      // Should see document details
      await expect(newPage.locator(`text=${testDocument.title}`)).toBeVisible();
      
      // Should have download link
      await expect(newPage.locator('a:has-text("Descargar")')).toBeVisible();
      
      await newPage.close();
    });
    
    // Step 9: Initiate transfer
    test.step('Initiate P2P transfer', async () => {
      await page.goto(`/transfer`);
      
      // Select operator
      await page.selectOption('select[name="destinationOperator"]', 'operator-test');
      
      // Select documents to transfer
      await page.check(`input[value="${documentId}"]`);
      
      await page.click('button:has-text("Iniciar Transferencia")');
      
      // Wait for transfer initiation
      await expect(page.locator('text=/transferencia iniciada/i')).toBeVisible({ timeout: 15000 });
    });
    
    // Step 10: Confirm transfer (mock destination operator response)
    test.step('Confirm transfer', async () => {
      // In real scenario, destination operator would confirm
      // For E2E, we mock the confirmation callback
      
      await page.route('**/api/transferCitizenConfirm', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            message: 'Transferencia confirmada',
            status: 1
          })
        });
      });
      
      // Simulate confirmation from destination
      await page.evaluate(() => {
        fetch('/api/transferCitizenConfirm', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            citizenId: '1234567890',
            token: 'mock-transfer-token',
            status: 1
          })
        });
      });
      
      // Wait for transfer completion
      await page.waitForTimeout(2000);
      
      // Verify transfer status
      await page.goto('/transfer/history');
      await expect(page.locator('text=/completada|confirmada/i')).toBeVisible();
    });
    
    // Step 11: Verify document no longer in source operator
    test.step('Verify document transferred', async () => {
      await page.goto('/documents');
      
      // Original document should not be visible (transferred)
      await expect(page.locator(`text=${testDocument.title}`)).not.toBeVisible();
    });
  });
  
  test('should handle errors gracefully', async ({ page }) => {
    // Test error scenarios
    
    test.step('Handle invalid citizen registration', async () => {
      await page.goto('/register');
      
      // Submit with invalid data
      await page.fill('input[name="identification"]', '123'); // Too short
      await page.click('button[type="submit"]');
      
      // Should show validation error
      await expect(page.locator('text=/identificación.*10 dígitos/i')).toBeVisible();
    });
    
    test.step('Handle upload failure', async () => {
      // Mock upload failure
      await page.route('**/api/documents/upload-url', async (route) => {
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ error: 'Upload failed' })
        });
      });
      
      await page.goto('/upload');
      await page.fill('input[name="title"]', 'Test');
      
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles({
        name: 'test.pdf',
        mimeType: 'application/pdf',
        buffer: Buffer.from('Test')
      });
      
      await page.click('button[type="submit"]');
      
      // Should show error message
      await expect(page.locator('text=/error.*subir/i')).toBeVisible();
    });
  });
  
  test('should respect rate limits', async ({ page }) => {
    test.step('Hit rate limit', async () => {
      await page.goto('/search');
      
      // Make many requests quickly
      for (let i = 0; i < 65; i++) {
        await page.fill('input[name="query"]', `Query ${i}`);
        await page.click('button:has-text("Buscar")');
        await page.waitForTimeout(100);
      }
      
      // Should eventually show rate limit error
      await expect(page.locator('text=/límite.*excedido|429/i')).toBeVisible({ timeout: 20000 });
    });
  });
});

test.describe('Performance Tests', () => {
  test('should load dashboard within 3 seconds', async ({ page }) => {
    const startTime = Date.now();
    
    await page.goto('/dashboard');
    
    const loadTime = Date.now() - startTime;
    
    expect(loadTime).toBeLessThan(3000);
  });
  
  test('should handle large document list', async ({ page }) => {
    // Mock large document list
    await page.route('**/api/metadata/documents*', async (route) => {
      const docs = Array.from({ length: 100 }, (_, i) => ({
        id: `doc-${i}`,
        title: `Document ${i}`,
        createdAt: new Date().toISOString()
      }));
      
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ documents: docs, total: 100 })
      });
    });
    
    await page.goto('/documents');
    
    // Should render without freezing
    await expect(page.locator('[data-testid="document-list"]')).toBeVisible();
    
    // Should have pagination
    await expect(page.locator('button:has-text("Siguiente")')).toBeVisible();
  });
});

