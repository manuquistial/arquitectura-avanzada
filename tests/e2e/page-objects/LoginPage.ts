import { Page, Locator } from '@playwright/test';

/**
 * Page Object Model for Login Page
 */
export class LoginPage {
  readonly page: Page;
  readonly loginButton: Locator;
  readonly emailInput: Locator;
  readonly passwordInput: Locator;
  readonly errorMessage: Locator;
  
  constructor(page: Page) {
    this.page = page;
    this.loginButton = page.locator('button:has-text("Iniciar")');
    this.emailInput = page.locator('input[name="email"]');
    this.passwordInput = page.locator('input[name="password"]');
    this.errorMessage = page.locator('[data-testid="error-message"]');
  }
  
  async goto() {
    await this.page.goto('/login');
  }
  
  async login(email: string, password: string) {
    await this.emailInput.fill(email);
    await this.passwordInput.fill(password);
    await this.loginButton.click();
  }
  
  async clickAzureB2CLogin() {
    await this.loginButton.click();
  }
  
  async hasError() {
    return await this.errorMessage.isVisible();
  }
}

