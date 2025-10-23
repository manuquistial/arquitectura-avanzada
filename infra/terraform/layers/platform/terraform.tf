# =============================================================================
# PLATFORM LAYER TERRAFORM CONFIGURATION
# =============================================================================

terraform {
  required_version = ">= 1.7"
  
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
  
  # Backend configuration (opcional)
  # backend "azurerm" {
  #   resource_group_name  = "terraform-state-rg"
  #   storage_account_name = "terraformstate"
  #   container_name       = "tfstate"
  #   key                  = "platform/terraform.tfstate"
  # }
}

# Provider configuration
provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }
  
  # Usar OIDC (Federated Identity) para autenticación en GitHub Actions
  use_oidc = true
  
  # Deshabilitar registro automático de Resource Providers
  resource_provider_registrations = "none"

  # Configurar subscription ID
  subscription_id = var.azure_subscription_id
}

# Provider para Azure AD
provider "azuread" {
  use_oidc = true
}
