# Azure AD B2C Tenant and Application Configuration
# Optimized for Azure for Students limitations

terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 3.0"
    }
  }
}

# Data source to get current tenant information
data "azurerm_client_config" "current" {}


# Azure AD B2C Tenant (if not exists, will be created via Azure Portal)
# Note: B2C tenants cannot be created via Terraform due to Azure limitations
# This module assumes the B2C tenant already exists

# Azure AD B2C Application Registration
resource "azuread_application" "carpeta_ciudadana" {
  display_name = "Carpeta Ciudadana - ${var.environment}"
  
  # Web application configuration
  web {
    redirect_uris = var.redirect_uris
    implicit_grant {
      access_token_issuance_enabled = true
      id_token_issuance_enabled     = true
    }
  }

  # API permissions
  required_resource_access {
    resource_app_id = "00000003-0000-0000-c000-000000000000" # Microsoft Graph

    resource_access {
      id   = "e1fe6dd8-ba31-4d61-89e7-88639da4683d" # User.Read
      type = "Scope"
    }
  }

  # Optional claims
  optional_claims {
    access_token {
      name                  = "email"
      essential             = true
    }
    
    id_token {
      name                  = "email"
      essential             = true
    }
  }

  tags = [
    "CarpetaCiudadana",
    var.environment,
    "B2C"
  ]
}

# Azure AD B2C Application Password (Client Secret)
resource "azuread_application_password" "carpeta_ciudadana" {
  application_id = azuread_application.carpeta_ciudadana.id
  display_name   = "Carpeta Ciudadana Secret - ${var.environment}"
  end_date       = timeadd(timestamp(), "8760h") # 1 year
}

# Azure AD B2C Service Principal
resource "azuread_service_principal" "carpeta_ciudadana" {
  client_id = azuread_application.carpeta_ciudadana.client_id
}

# Azure AD B2C User Flow (B2C_1_signupsignin)
# Note: User flows cannot be created via Terraform
# They must be created manually in Azure Portal or via Azure CLI

# Local values for outputs
locals {
  b2c_tenant_name = var.b2c_tenant_name
  b2c_tenant_id   = data.azurerm_client_config.current.tenant_id
  client_id       = azuread_application.carpeta_ciudadana.client_id
  client_secret   = azuread_application_password.carpeta_ciudadana.value
}

