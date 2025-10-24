# =============================================================================
# APPLICATION SECRETS MODULE
# =============================================================================
# Este módulo maneja los secrets específicos de la aplicación:
# - M2M Authentication
# - JWT
# - NextAuth
# - API Keys
# =============================================================================

terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
}

# Random IDs for application secrets
resource "random_id" "m2m_suffix" {
  byte_length = 4
}

resource "random_id" "jwt_suffix" {
  byte_length = 4
}

resource "random_id" "nextauth_suffix" {
  byte_length = 4
}

resource "random_id" "api_suffix" {
  byte_length = 4
}

# Application secrets in Key Vault
resource "azurerm_key_vault_secret" "application_secrets" {
  for_each = var.application_secrets

  name         = each.key
  value        = each.value
  key_vault_id = var.key_vault_id

  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
    Layer       = "Application"
  }
}

# M2M Authentication secret
resource "azurerm_key_vault_secret" "m2m_auth" {
  name         = "m2m-auth"
  value        = jsonencode({
    "secret-key" = "m2m-secret-key-${random_id.m2m_suffix.hex}"
    "max-timestamp-age" = "300"
    "nonce-ttl" = "600"
  })
  key_vault_id = var.key_vault_id

  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
    Layer       = "Application"
    Service     = "M2M-Auth"
  }
}

# JWT secret
resource "azurerm_key_vault_secret" "jwt" {
  name         = "jwt"
  value        = jsonencode({
    "secret-key" = "jwt-secret-key-${random_id.jwt_suffix.hex}"
  })
  key_vault_id = var.key_vault_id

  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
    Layer       = "Application"
    Service     = "JWT"
  }
}

# NextAuth secret
resource "azurerm_key_vault_secret" "nextauth" {
  name         = "nextauth"
  value        = jsonencode({
    "secret" = "nextauth-secret-${random_id.nextauth_suffix.hex}"
    "url"    = var.nextauth_url
  })
  key_vault_id = var.key_vault_id

  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
    Layer       = "Application"
    Service     = "NextAuth"
  }
}

# API Keys secret
resource "azurerm_key_vault_secret" "api_keys" {
  name         = "api-keys"
  value        = jsonencode({
    "operator-api-key" = "operator-api-key-${random_id.api_suffix.hex}"
  })
  key_vault_id = var.key_vault_id

  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
    Layer       = "Application"
    Service     = "API-Keys"
  }
}
