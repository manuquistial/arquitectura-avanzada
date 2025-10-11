resource "azurerm_storage_account" "main" {
  name                     = "${replace(var.environment, "-", "")}carpetastorage"
  resource_group_name      = var.resource_group_name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  
  blob_properties {
    versioning_enabled = true
    
    delete_retention_policy {
      days = 7
    }
  }
  
  tags = {
    Environment = var.environment
  }
}

resource "azurerm_storage_container" "documents" {
  name                  = "documents"
  storage_account_name  = azurerm_storage_account.main.name
  container_access_type = "private"
}

# CORS para permitir uploads desde frontend
resource "azurerm_storage_account_cors_rule" "main" {
  storage_account_id = azurerm_storage_account.main.id
  service            = "blob"
  
  cors_rule {
    allowed_origins    = ["*"]
    allowed_methods    = ["GET", "PUT", "POST", "DELETE", "HEAD"]
    allowed_headers    = ["*"]
    exposed_headers    = ["*"]
    max_age_in_seconds = 3600
  }
}

