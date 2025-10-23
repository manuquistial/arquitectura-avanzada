resource "random_string" "storage_suffix" {
  length  = 4
  special = false
  upper   = false
}

resource "azurerm_storage_account" "main" {
  name                     = "${replace(var.environment, "-", "")}ccstorage${random_string.storage_suffix.result}"
  resource_group_name      = var.resource_group_name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"
  
  # Enable infrastructure encryption for additional security
  infrastructure_encryption_enabled = var.enable_infrastructure_encryption
  
  # Enable cross-tenant replication for backup
  cross_tenant_replication_enabled = var.enable_cross_tenant_replication

  blob_properties {
    versioning_enabled = true

    delete_retention_policy {
      days = var.blob_delete_retention_days
    }
    
    # Enable change feed for audit
    change_feed_enabled = var.enable_change_feed
    change_feed_retention_in_days = var.enable_change_feed ? var.change_feed_retention_days : null

    # CORS restrictivo - Solo orígenes específicos en producción
    cors_rule {
      allowed_origins    = var.cors_allowed_origins
      allowed_methods    = var.cors_allowed_methods
      allowed_headers    = var.cors_allowed_headers
      exposed_headers    = var.cors_exposed_headers
      max_age_in_seconds = var.cors_max_age_in_seconds
    }
  }

  tags = {
    Environment = var.environment
    Security    = "MicrosoftDefenderEnabled"
  }
}

resource "azurerm_storage_container" "documents" {
  name                  = "documents"
  storage_account_id    = azurerm_storage_account.main.id
  container_access_type = "private"
}

# Microsoft Defender for Storage
# Note: Security Center pricing is configured manually via Azure CLI

# Microsoft Defender for Storage - Storage Account Protection
resource "azurerm_security_center_storage_defender" "main" {
  count = var.enable_defender_for_storage ? 1 : 0
  
  storage_account_id = azurerm_storage_account.main.id
  malware_scanning_on_upload_enabled = var.enable_malware_scanning
  sensitive_data_discovery_enabled   = var.enable_sensitive_data_discovery
  override_subscription_settings_enabled = var.override_subscription_settings
}

# Security Center Auto Provisioning for Storage
# Note: azurerm_security_center_auto_provisioning is deprecated in AzureRM v4.0+
# and will be removed in v5.0. Configure auto-provisioning manually in Azure Portal
# resource "azurerm_security_center_auto_provisioning" "storage" {
#   count = var.enable_defender_for_storage ? 1 : 0
#   
#   auto_provision = "On"
# }

# Security Center Contact for Storage Alerts
# Note: Security Center contact is configured manually via Azure CLI

# Storage Account Network Rules for Enhanced Security
resource "azurerm_storage_account_network_rules" "main" {
  count = var.enable_storage_network_rules ? 1 : 0
  
  storage_account_id = azurerm_storage_account.main.id
  
  default_action             = "Deny"
  ip_rules                   = var.allowed_ip_addresses
  virtual_network_subnet_ids = var.allowed_subnet_ids
  bypass                     = ["AzureServices"]
}


