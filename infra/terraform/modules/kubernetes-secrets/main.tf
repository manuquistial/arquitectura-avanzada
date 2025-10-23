# Kubernetes Secrets para PostgreSQL Private Endpoint
# Este módulo crea los secrets necesarios para la conexión privada

# Secret para PostgreSQL
resource "kubernetes_secret" "postgresql_secret" {
  metadata {
    name      = "postgresql-secret"
    namespace = var.namespace
  }

  data = {
    PGHOST     = var.postgresql_fqdn
    PGUSER     = var.postgresql_username
    PGPASSWORD = var.postgresql_password
    PGDATABASE = var.postgresql_database
    PGPORT     = "5432"
    PGSSLMODE  = "require"
  }

  type = "Opaque"
}

# Secret para Azure Storage
resource "kubernetes_secret" "azure_storage_secret" {
  count = var.azure_storage_enabled ? 1 : 0

  metadata {
    name      = "azure-storage-secret"
    namespace = var.namespace
  }

  data = {
    AZURE_STORAGE_ACCOUNT_NAME    = var.azure_storage_account_name
    AZURE_STORAGE_ACCOUNT_KEY     = var.azure_storage_account_key
    AZURE_STORAGE_CONTAINER_NAME  = var.azure_storage_container_name
  }

  type = "Opaque"
}

# Secret para Service Bus
resource "kubernetes_secret" "servicebus_secret" {
  count = var.servicebus_enabled ? 1 : 0

  metadata {
    name      = "servicebus-secret"
    namespace = var.namespace
  }

  data = {
    SERVICEBUS_CONNECTION_STRING = var.servicebus_connection_string
  }

  type = "Opaque"
}

# Secret para Redis
resource "kubernetes_secret" "redis_secret" {
  count = var.redis_enabled ? 1 : 0

  metadata {
    name      = "redis-secret"
    namespace = var.namespace
  }

  data = {
    REDIS_HOST     = var.redis_host
    REDIS_PORT     = var.redis_port
    REDIS_PASSWORD = var.redis_password
    REDIS_SSL      = var.redis_ssl
  }

  type = "Opaque"
}

# Secret para Azure AD B2C
resource "kubernetes_secret" "azure_b2c_secret" {
  count = var.azure_b2c_enabled ? 1 : 0

  metadata {
    name      = "azure-b2c-secret"
    namespace = var.namespace
  }

  data = {
    AZURE_B2C_TENANT_ID     = var.azure_b2c_tenant_id
    AZURE_B2C_CLIENT_ID     = var.azure_b2c_client_id
    AZURE_B2C_CLIENT_SECRET = var.azure_b2c_client_secret
  }

  type = "Opaque"
}

# Secret para M2M Authentication
resource "kubernetes_secret" "m2m_secret" {
  metadata {
    name      = "m2m-secret"
    namespace = var.namespace
  }

  data = {
    M2M_SECRET_KEY = var.m2m_secret_key
  }

  type = "Opaque"
}
