# =============================================================================
# BASE LAYER TERRAFORM CONFIGURATION
# =============================================================================

terraform {
  required_version = ">= 1.7"
  
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
  
  # Backend configuration (opcional)
  # backend "azurerm" {
  #   resource_group_name  = "terraform-state-rg"
  #   storage_account_name = "terraformstate"
  #   container_name       = "tfstate"
  #   key                  = "base/terraform.tfstate"
  # }
}
