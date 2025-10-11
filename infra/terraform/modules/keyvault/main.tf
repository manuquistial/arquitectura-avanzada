resource "azurerm_key_vault" "main" {
  name                = "${var.environment}-kv-${random_string.suffix.result}"
  location            = var.location
  resource_group_name = var.resource_group_name
  tenant_id           = var.tenant_id
  sku_name            = "standard"
  
  purge_protection_enabled   = false
  soft_delete_retention_days = 7
  
  access_policy {
    tenant_id = var.tenant_id
    object_id = var.tenant_id
    
    certificate_permissions = [
      "Get", "List", "Create", "Import", "Delete", "Purge"
    ]
    
    secret_permissions = [
      "Get", "List", "Set", "Delete", "Purge"
    ]
  }
  
  tags = {
    Environment = var.environment
  }
}

resource "random_string" "suffix" {
  length  = 4
  special = false
  upper   = false
}

