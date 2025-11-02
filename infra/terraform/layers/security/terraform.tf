# =============================================================================
# SECURITY LAYER TERRAFORM CONFIGURATION
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
}

provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }

  use_oidc                         = true
  resource_provider_registrations = "none"
  subscription_id                  = var.azure_subscription_id
}

provider "azuread" {
  use_oidc = true
}


