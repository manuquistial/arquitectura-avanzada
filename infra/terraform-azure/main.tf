terraform {
  required_version = ">= 1.6"
  
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.80"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 2.45"
    }
  }

  backend "azurerm" {
    resource_group_name  = "carpeta-ciudadana-tfstate-rg"
    storage_account_name = "carpetaciudadanatfstate"
    container_name       = "tfstate"
    key                  = "terraform.tfstate"
  }
}

provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }
}

# Resource Group principal
resource "azurerm_resource_group" "main" {
  name     = "${var.project_name}-${var.environment}-rg"
  location = var.azure_region

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Virtual Network
module "vnet" {
  source = "./modules/vnet"

  environment         = var.environment
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  vnet_cidr           = var.vnet_cidr
  subnet_cidrs        = var.subnet_cidrs
}

# AKS (Kubernetes)
module "aks" {
  source = "./modules/aks"

  environment         = var.environment
  cluster_name        = "${var.project_name}-${var.environment}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  subnet_id           = module.vnet.aks_subnet_id
  node_count          = var.aks_node_count
  vm_size             = var.aks_vm_size
}

# PostgreSQL Flexible Server
module "postgresql" {
  source = "./modules/postgresql"

  environment         = var.environment
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  subnet_id           = module.vnet.db_subnet_id
  admin_username      = var.db_admin_username
  admin_password      = var.db_admin_password
  sku_name            = var.db_sku_name
  storage_mb          = var.db_storage_mb
}

# Blob Storage
module "storage" {
  source = "./modules/storage"

  environment         = var.environment
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
}

# Azure Cognitive Search (equivalente a OpenSearch)
module "search" {
  source = "./modules/search"

  environment         = var.environment
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = var.search_sku
}

# Service Bus (equivalente a SQS/SNS)
module "servicebus" {
  source = "./modules/servicebus"

  environment         = var.environment
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = var.servicebus_sku
}

# Azure AD B2C (equivalente a Cognito)
module "adb2c" {
  source = "./modules/adb2c"

  environment         = var.environment
  resource_group_name = azurerm_resource_group.main.name
  domain_name         = var.adb2c_domain_name
}

# Container Registry (ACR - equivalente a ECR)
module "acr" {
  source = "./modules/acr"

  environment         = var.environment
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = var.acr_sku
}

# Key Vault (para certificados mTLS)
module "keyvault" {
  source = "./modules/keyvault"

  environment         = var.environment
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  tenant_id           = data.azurerm_client_config.current.tenant_id
}

# Managed Identity para AKS
resource "azurerm_user_assigned_identity" "aks_identity" {
  name                = "${var.project_name}-${var.environment}-aks-identity"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
}

# Role assignments para Managed Identity
resource "azurerm_role_assignment" "aks_to_acr" {
  scope                = module.acr.acr_id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.aks_identity.principal_id
}

resource "azurerm_role_assignment" "aks_to_storage" {
  scope                = module.storage.storage_account_id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.aks_identity.principal_id
}

# Data sources
data "azurerm_client_config" "current" {}

