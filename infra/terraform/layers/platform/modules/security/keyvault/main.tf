# Azure Key Vault Module
# Configuración completa para Azure Key Vault con External Secrets Operator

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

# Data source para obtener información del tenant actual
data "azurerm_client_config" "current" {}

# Azure Key Vault con RBAC habilitado
resource "azurerm_key_vault" "main" {
  name                = var.keyvault_name
  location            = var.location
  resource_group_name = var.resource_group_name
  tenant_id           = data.azurerm_client_config.current.tenant_id
  sku_name            = var.sku_name
  
  # Security configuration
  purge_protection_enabled   = var.purge_protection_enabled
  soft_delete_retention_days = var.soft_delete_retention_days
  
  # HABILITAR RBAC (más moderno y seguro que access policies)
  rbac_authorization_enabled = true
  
  # Network access
  network_acls {
    default_action = var.network_acls_default_action
    bypass         = var.network_acls_bypass
    
    # Permitir acceso desde AKS
    virtual_network_subnet_ids = var.allowed_subnet_ids
    
    # Permitir acceso desde IPs específicas
    ip_rules = var.allowed_ip_rules
  }
  
  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
    Service     = "Key Vault"
  }
}

# Managed Identity para External Secrets Operator
resource "azurerm_user_assigned_identity" "external_secrets" {
  name                = "${var.keyvault_name}-external-secrets"
  resource_group_name = var.resource_group_name
  location            = var.location
  
  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
    Service     = "External Secrets"
  }
}

# =============================================================================
# RBAC (Role-Based Access Control) - MÁS MODERNO Y SEGURO
# =============================================================================

# Asignar rol "Key Vault Secrets Officer" al usuario actual (para Terraform)
resource "azurerm_role_assignment" "terraform_user_secrets_officer" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = data.azurerm_client_config.current.object_id
  
  description = "Permite a Terraform gestionar secrets en Key Vault"
}

# Asignar rol "Key Vault Secrets User" al Managed Identity de External Secrets
resource "azurerm_role_assignment" "external_secrets_secrets_user" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.external_secrets.principal_id
  
  description = "Permite a External Secrets Operator leer secrets"
}

# Asignar rol "Key Vault Secrets Officer" al Managed Identity de External Secrets (para gestión completa)
resource "azurerm_role_assignment" "external_secrets_secrets_officer" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = azurerm_user_assigned_identity.external_secrets.principal_id
  
  description = "Permite a External Secrets Operator gestionar secrets completamente"
}

# Role assignment de AKS movido a APPLICATION LAYER
# para evitar dependencias circulares

# Crear secrets iniciales en Key Vault (opcional)
resource "azurerm_key_vault_secret" "initial_secrets" {
  for_each = var.initial_secrets
  
  name         = each.key
  value        = each.value
  key_vault_id = azurerm_key_vault.main.id
  
  depends_on = [
    azurerm_key_vault.main
  ]
  
  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Federated Identity Credential para External Secrets Operator
resource "azuread_application" "external_secrets" {
  display_name = "${var.keyvault_name}-external-secrets-app"
  
  # Configuración para Workload Identity
  web {
    redirect_uris = []
  }
  
  tags = [
    "External Secrets",
    var.environment
  ]
}

resource "azuread_service_principal" "external_secrets" {
  client_id = azuread_application.external_secrets.client_id
}

# Federated Identity Credential - Commented out due to provider version issue
# resource "azuread_service_principal_federated_identity_credential" "external_secrets" {
#   service_principal_id = azuread_service_principal.external_secrets.object_id
#   display_name         = "external-secrets-federated-credential"
#   description          = "Federated identity credential for External Secrets Operator"
#   audiences            = ["api://AzureADTokenExchange"]
#   issuer               = var.aks_oidc_issuer_url
#   subject              = "system:serviceaccount:${var.external_secrets_namespace}:external-secrets"
# }

# Asignar el Managed Identity al Service Principal
resource "azurerm_role_assignment" "external_secrets_identity" {
  scope                = azurerm_user_assigned_identity.external_secrets.id
  role_definition_name = "Managed Identity Operator"
  principal_id         = azuread_service_principal.external_secrets.object_id
}
