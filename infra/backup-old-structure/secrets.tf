# =============================================================================
# CONFIGURACIÓN DE SECRETS PARA AZURE KEY VAULT CON RBAC
# =============================================================================
# Este archivo define todos los secrets que se crearán en Azure Key Vault
# usando RBAC (Role-Based Access Control) en lugar de access policies
# 
# VENTAJAS DE RBAC:
# - Más moderno y seguro
# - Integrado con Azure AD
# - Permisos granulares por rol
# - Fácil de auditar
# - Compatible con Azure Policy
# =============================================================================

# Generar secrets aleatorios
resource "random_password" "jwt_secret" {
  length  = 64
  special = true
}

resource "random_password" "m2m_secret" {
  length  = 32
  special = true
}

resource "random_password" "nextauth_secret" {
  length  = 32
  special = true
}

resource "random_password" "operator_api_key" {
  length  = 32
  special = true
}

# =============================================================================
# SECRETS CONFIGURATION - USANDO RBAC
# =============================================================================
# Los secrets se crean con permisos RBAC en lugar de access policies
# Esto es más seguro y moderno

# Secrets de Base de Datos
resource "azurerm_key_vault_secret" "database_secrets" {
  name         = "database-secrets"
  value        = module.postgresql.connection_string_uri
  key_vault_id = module.keyvault[0].key_vault_id
  
  # Depender de los role assignments RBAC
  depends_on = [
    module.keyvault
  ]
  
  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
    Component   = "Database"
  }
}

resource "azurerm_key_vault_secret" "postgres_uri" {
  name         = "postgres-uri"
  value        = module.postgresql.connection_string_uri
  key_vault_id = module.keyvault[0].key_vault_id
  
  # Depender de los role assignments RBAC
  depends_on = [
    module.keyvault
  ]
  
  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
    Component   = "Database"
  }
}

resource "azurerm_key_vault_secret" "db_host" {
  name         = "db-host"
  value        = module.postgresql.fqdn
  key_vault_id = module.keyvault[0].key_vault_id
  
  # Depender de los role assignments RBAC
  depends_on = [
    module.keyvault
  ]
  
  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
    Component   = "Database"
  }
}

resource "azurerm_key_vault_secret" "db_port" {
  name         = "db-port"
  value        = "5432"
  key_vault_id = module.keyvault[0].key_vault_id
  
  # Depender de los role assignments RBAC
  depends_on = [
    module.keyvault
  ]
  
  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
    Component   = "Database"
  }
}

resource "azurerm_key_vault_secret" "db_name" {
  name         = "db-name"
  value        = "carpeta_ciudadana"
  key_vault_id = module.keyvault[0].key_vault_id
  
  # Depender de los role assignments RBAC
  depends_on = [
    module.keyvault
  ]
  
  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
    Component   = "Database"
  }
}

resource "azurerm_key_vault_secret" "db_user" {
  name         = "db-user"
  value        = "carpeta_admin"
  key_vault_id = module.keyvault[0].key_vault_id
  
  # Depender de los role assignments RBAC
  depends_on = [
    module.keyvault
  ]
  
  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
    Component   = "Database"
  }
}

resource "azurerm_key_vault_secret" "db_password" {
  name         = "db-password"
  value        = var.db_admin_password
  key_vault_id = module.keyvault[0].key_vault_id
  
  # Depender de los role assignments RBAC
  depends_on = [
    module.keyvault
  ]
  
  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
    Component   = "Database"
  }
}

resource "azurerm_key_vault_secret" "db_sslmode" {
  name         = "db-sslmode"
  value        = "require"
  key_vault_id = module.keyvault[0].key_vault_id
  
  # Depender de los role assignments RBAC
  depends_on = [
    module.keyvault
  ]
  
  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
    Component   = "Database"
  }
}

# Secrets de Azure Storage

resource "azurerm_key_vault_secret" "storage_account_name" {
  name         = "account-name"
  value        = module.storage.storage_account_name
  key_vault_id = module.keyvault[0].key_vault_id
  
  # Depender de los role assignments RBAC
  depends_on = [
    module.keyvault
  ]
  
  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
    Component   = "Storage"
  }
}

resource "azurerm_key_vault_secret" "storage_account_key" {
  name         = "account-key"
  value        = module.storage.primary_access_key
  key_vault_id = module.keyvault[0].key_vault_id
  
  # Depender de los role assignments RBAC
  depends_on = [
    module.keyvault
  ]
  
  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
    Component   = "Storage"
  }
}

resource "azurerm_key_vault_secret" "storage_container_name" {
  name         = "container-name"
  value        = "documents"
  key_vault_id = module.keyvault[0].key_vault_id
  
  # Depender de los role assignments RBAC
  depends_on = [
    module.keyvault
  ]
  
  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
    Component   = "Storage"
  }
}

# Secrets de Service Bus - REMOVED

resource "azurerm_key_vault_secret" "redis_host" {
  name         = "host"
  value        = module.redis[0].redis_hostname
  key_vault_id = module.keyvault[0].key_vault_id
  
  # Depender de los role assignments RBAC
  depends_on = [
    module.keyvault
  ]
  
  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
    Component   = "Redis"
  }
}

resource "azurerm_key_vault_secret" "redis_port" {
  name         = "port"
  value        = "6380"
  key_vault_id = module.keyvault[0].key_vault_id
  
  # Depender de los role assignments RBAC
  depends_on = [
    module.keyvault
  ]
  
  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
    Component   = "Redis"
  }
}

resource "azurerm_key_vault_secret" "redis_ssl" {
  name         = "ssl"
  value        = "true"
  key_vault_id = module.keyvault[0].key_vault_id
  
  # Depender de los role assignments RBAC
  depends_on = [
    module.keyvault
  ]
  
  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
    Component   = "Redis"
  }
}

resource "azurerm_key_vault_secret" "redis_password" {
  name         = "password"
  value        = module.redis[0].redis_primary_key
  key_vault_id = module.keyvault[0].key_vault_id
  
  # Depender de los role assignments RBAC
  depends_on = [
    module.keyvault
  ]
  
  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
    Component   = "Redis"
  }
}

resource "azurerm_key_vault_secret" "redis_session_db" {
  name         = "session-db"
  value        = "0"
  key_vault_id = module.keyvault[0].key_vault_id
  
  # Depender de los role assignments RBAC
  depends_on = [
    module.keyvault
  ]
  
  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
    Component   = "Redis"
  }
}

# Secrets de Azure AD B2C - REMOVED

# Secrets generados automáticamente
resource "azurerm_key_vault_secret" "jwt_secret" {
  name         = "jwt-secret"
  value        = random_password.jwt_secret.result
  key_vault_id = module.keyvault[0].key_vault_id
  
  # Depender de los role assignments RBAC
  depends_on = [
    module.keyvault
  ]
  
  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
    Component   = "JWT"
  }
}

resource "azurerm_key_vault_secret" "m2m_secret" {
  name         = "m2m-secret"
  value        = random_password.m2m_secret.result
  key_vault_id = module.keyvault[0].key_vault_id
  
  # Depender de los role assignments RBAC
  depends_on = [
    module.keyvault
  ]
  
  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
    Component   = "M2M"
  }
}

resource "azurerm_key_vault_secret" "nextauth_secret" {
  name         = "nextauth-secret"
  value        = random_password.nextauth_secret.result
  key_vault_id = module.keyvault[0].key_vault_id
  
  # Depender de los role assignments RBAC
  depends_on = [
    module.keyvault
  ]
  
  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
    Component   = "NextAuth"
  }
}

resource "azurerm_key_vault_secret" "nextauth_url" {
  name         = "nextauth-url"
  value        = var.nextauth_url
  key_vault_id = module.keyvault[0].key_vault_id
  
  # Depender de los role assignments RBAC
  depends_on = [
    module.keyvault
  ]
  
  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
    Component   = "NextAuth"
  }
}

resource "azurerm_key_vault_secret" "operator_api_key" {
  name         = "operator-api-key"
  value        = random_password.operator_api_key.result
  key_vault_id = module.keyvault[0].key_vault_id
  
  # Depender de los role assignments RBAC
  depends_on = [
    module.keyvault
  ]
  
  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
    Component   = "API"
  }
}
