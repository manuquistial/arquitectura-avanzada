import { Page, Locator } from '@playwright/test';

/**
 * Page Object Model for Documents Page
 */
export class DocumentsPage {
  readonly page: Page;
  readonly uploadButton: Locator;
  readonly documentsList: Locator;
  readonly searchInput: Locator;
  readonly filterSelect: Locator;
  
  constructor(page: Page) {
    this.page = page;
    this.uploadButton = page.locator('button:has-text("Subir")');
    this.documentsList = page.locator('[data-testid="documents-list"]');
    this.searchInput = page.locator('input[placeholder*="Buscar"]');
    this.filterSelect = page.locator('select[name="filter"]');
  }
  
  async goto() {
    await this.page.goto('/documents');
  }
  
  async uploadDocument(filename: string, buffer: Buffer, docType: string = 'cedula') {
    await this.uploadButton.click();
    
    const fileInput = this.page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: filename,
      mimeType: 'application/pdf',
      buffer: buffer
    });
    
    await this.page.selectOption('select[name="document_type"]', docType);
    await this.page.click('button:has-text("Cargar")');
  }
  
  async searchDocuments(query: string) {
    await this.searchInput.fill(query);
    await this.page.keyboard.press('Enter');
  }
  
  async filterBy(filter: string) {
    await this.filterSelect.selectOption(filter);
  }
  
  async selectDocument(index: number = 0) {
    const row = this.page.locator('[data-testid="document-row"]').nth(index);
    await row.click();
  }
  
  async getDocumentCount() {
    return await this.page.locator('[data-testid="document-row"]').count();
  }
  
  async downloadDocument(index: number = 0) {
    const downloadPromise = this.page.waitForEvent('download');
    
    const row = this.page.locator('[data-testid="document-row"]').nth(index);
    await row.locator('button:has-text("Descargar")').click();
    
    return await downloadPromise;
  }
  
  async deleteDocument(index: number = 0) {
    const row = this.page.locator('[data-testid="document-row"]').nth(index);
    await row.locator('button:has-text("Eliminar")').click();
    
    // Confirm deletion
    await this.page.click('button:has-text("Confirmar")');
  }
}

