resource "azurerm_storage_account" "main" {
  name                     = "${replace(var.environment, "-", "")}carpetastorage"
  resource_group_name      = var.resource_group_name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"

  blob_properties {
    versioning_enabled = true
    
    delete_retention_policy {
      days = 7
    }
    
    # CORS restrictivo - Solo orígenes específicos en producción
    cors_rule {
      allowed_origins    = ["https://${var.domain_name}", "http://localhost:3000"]
      allowed_methods    = ["GET", "PUT", "HEAD"]
      allowed_headers    = ["Content-Type", "x-ms-blob-type", "x-ms-blob-content-type"]
      exposed_headers    = ["x-ms-request-id", "x-ms-version"]
      max_age_in_seconds = 3600
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

