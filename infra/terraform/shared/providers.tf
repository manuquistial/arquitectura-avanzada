# =============================================================================
# SHARED PROVIDERS CONFIGURATION
# =============================================================================
# Configuración compartida de providers para todas las capas
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
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.12"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.24"
    }
    time = {
      source  = "hashicorp/time"
      version = "~> 0.10"
    }
  }
}

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

# Provider para Helm
# Uses kubeconfig file from environment (generated after AKS creation)
# For initial deployment, use two-stage apply (see CI/CD pipeline)
provider "helm" {
  kubernetes {
    config_path = "~/.kube/config"
    config_context = "carpeta-ciudadana-${var.environment}-admin"
  }
}

# Provider para Kubernetes  
# Uses kubeconfig file from environment (generated after AKS creation)
# For initial deployment, use two-stage apply (see CI/CD pipeline)
provider "kubernetes" {
  config_path = "~/.kube/config"
  config_context = "carpeta-ciudadana-${var.environment}-admin"
}

# Data sources
data "azurerm_client_config" "current" {}

# Get current IP address for firewall rules
data "http" "current_ip" {
  url = "https://ipv4.icanhazip.com"
}


