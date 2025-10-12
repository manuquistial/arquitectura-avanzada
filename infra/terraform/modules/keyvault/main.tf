/**
 * Azure Key Vault Module
 * 
 * Stores secrets securely:
 * - Database credentials
 * - Service Bus connection strings
 * - M2M authentication keys
 * - API keys
 * - Certificates
 */

terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.80"
    }
  }
}

data "azurerm_client_config" "current" {}

# Key Vault
resource "azurerm_key_vault" "main" {
  name                = "${var.project_name}-${var.environment}-kv"
  location            = var.location
  resource_group_name = var.resource_group_name
  tenant_id           = var.tenant_id
  sku_name            = var.sku_name

  # Soft delete (required for production)
  soft_delete_retention_days = var.soft_delete_retention_days
  purge_protection_enabled   = var.purge_protection_enabled

  # Network ACLs
  network_acls {
    bypass                     = "AzureServices"
    default_action             = var.enable_public_access ? "Allow" : "Deny"
    ip_rules                   = var.allowed_ip_ranges
    virtual_network_subnet_ids = var.allowed_subnet_ids
  }

  # Enable RBAC (recommended over access policies)
  enable_rbac_authorization = var.enable_rbac

  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Role assignment for AKS Managed Identity (Workload Identity)
resource "azurerm_role_assignment" "aks_kv_secrets_user" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = var.aks_identity_principal_id
}

# Additional role for certificate operations (if needed)
resource "azurerm_role_assignment" "aks_kv_certificates_user" {
  count                = var.enable_certificate_access ? 1 : 0
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Certificates User"
  principal_id         = var.aks_identity_principal_id
}

# Secrets - Database
resource "azurerm_key_vault_secret" "postgres_host" {
  name         = "postgres-host"
  value        = var.postgres_host
  key_vault_id = azurerm_key_vault.main.id

  depends_on = [azurerm_role_assignment.aks_kv_secrets_user]
}

resource "azurerm_key_vault_secret" "postgres_username" {
  name         = "postgres-username"
  value        = var.postgres_username
  key_vault_id = azurerm_key_vault.main.id

  depends_on = [azurerm_role_assignment.aks_kv_secrets_user]
}

resource "azurerm_key_vault_secret" "postgres_password" {
  name         = "postgres-password"
  value        = var.postgres_password
  key_vault_id = azurerm_key_vault.main.id

  depends_on = [azurerm_role_assignment.aks_kv_secrets_user]
}

resource "azurerm_key_vault_secret" "postgres_database" {
  name         = "postgres-database"
  value        = var.postgres_database
  key_vault_id = azurerm_key_vault.main.id

  depends_on = [azurerm_role_assignment.aks_kv_secrets_user]
}

# Secrets - Service Bus
resource "azurerm_key_vault_secret" "servicebus_connection_string" {
  name         = "servicebus-connection-string"
  value        = var.servicebus_connection_string
  key_vault_id = azurerm_key_vault.main.id

  depends_on = [azurerm_role_assignment.aks_kv_secrets_user]
}

# Secrets - M2M Authentication
resource "azurerm_key_vault_secret" "m2m_secret_key" {
  name         = "m2m-secret-key"
  value        = var.m2m_secret_key
  key_vault_id = azurerm_key_vault.main.id

  depends_on = [azurerm_role_assignment.aks_kv_secrets_user]
}

# Secrets - Azure Storage
resource "azurerm_key_vault_secret" "storage_account_name" {
  name         = "storage-account-name"
  value        = var.storage_account_name
  key_vault_id = azurerm_key_vault.main.id

  depends_on = [azurerm_role_assignment.aks_kv_secrets_user]
}

# Secrets - Redis
resource "azurerm_key_vault_secret" "redis_password" {
  count        = var.redis_password != "" ? 1 : 0
  name         = "redis-password"
  value        = var.redis_password
  key_vault_id = azurerm_key_vault.main.id

  depends_on = [azurerm_role_assignment.aks_kv_secrets_user]
}

# Secrets - OpenSearch
resource "azurerm_key_vault_secret" "opensearch_username" {
  name         = "opensearch-username"
  value        = var.opensearch_username
  key_vault_id = azurerm_key_vault.main.id

  depends_on = [azurerm_role_assignment.aks_kv_secrets_user]
}

resource "azurerm_key_vault_secret" "opensearch_password" {
  name         = "opensearch-password"
  value        = var.opensearch_password
  key_vault_id = azurerm_key_vault.main.id

  depends_on = [azurerm_role_assignment.aks_kv_secrets_user]
}

# Secrets - Azure AD B2C
resource "azurerm_key_vault_secret" "azure_b2c_tenant_id" {
  count        = var.azure_b2c_tenant_id != "" ? 1 : 0
  name         = "azure-b2c-tenant-id"
  value        = var.azure_b2c_tenant_id
  key_vault_id = azurerm_key_vault.main.id

  depends_on = [azurerm_role_assignment.aks_kv_secrets_user]
}

resource "azurerm_key_vault_secret" "azure_b2c_client_id" {
  count        = var.azure_b2c_client_id != "" ? 1 : 0
  name         = "azure-b2c-client-id"
  value        = var.azure_b2c_client_id
  key_vault_id = azurerm_key_vault.main.id

  depends_on = [azurerm_role_assignment.aks_kv_secrets_user]
}

resource "azurerm_key_vault_secret" "azure_b2c_client_secret" {
  count        = var.azure_b2c_client_secret != "" ? 1 : 0
  name         = "azure-b2c-client-secret"
  value        = var.azure_b2c_client_secret
  key_vault_id = azurerm_key_vault.main.id

  depends_on = [azurerm_role_assignment.aks_kv_secrets_user]
}

# Diagnostic settings (optional, for monitoring)
resource "azurerm_monitor_diagnostic_setting" "kv_diagnostics" {
  count                      = var.enable_diagnostics ? 1 : 0
  name                       = "${azurerm_key_vault.main.name}-diagnostics"
  target_resource_id         = azurerm_key_vault.main.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  enabled_log {
    category = "AuditEvent"
  }

  metric {
    category = "AllMetrics"
    enabled  = true
  }
}

