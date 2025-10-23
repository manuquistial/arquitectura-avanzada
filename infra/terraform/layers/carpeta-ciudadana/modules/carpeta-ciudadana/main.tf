# Carpeta Ciudadana Helm Chart Module

# Helm Release for Carpeta Ciudadana
resource "helm_release" "carpeta_ciudadana" {
  name       = "carpeta-ciudadana"
  chart      = var.chart_path
  version    = var.chart_version
  namespace  = var.namespace
  create_namespace = true
  timeout    = var.timeout

  values = [
    file("${var.chart_path}/values.yaml")
  ]

  # Valores dinámicos para Key Vault
  set {
    name  = "keyvault.vaultUrl"
    value = var.key_vault_uri
  }

  set {
    name  = "keyvault.clientId"
    value = var.workload_identity_client_id
  }

  set {
    name  = "global.workloadIdentity.clientId"
    value = var.workload_identity_client_id
  }

  set {
    name  = "global.workloadIdentity.tenantId"
    value = var.workload_identity_tenant_id
  }

  # Dependencias manejadas por el layer principal
}

# Kubernetes Secret for database credentials
resource "kubernetes_secret" "database_credentials" {
  metadata {
    name      = "database-credentials"
    namespace = var.namespace
  }

  data = {
    username = var.database_username
    password = var.database_password
  }

  type = "Opaque"
}

# Kubernetes Secret for Redis credentials
resource "kubernetes_secret" "redis_credentials" {
  metadata {
    name      = "redis-credentials"
    namespace = var.namespace
  }

  data = {
    password = var.redis_password
  }

  type = "Opaque"
}

# Kubernetes Secret for storage credentials
resource "kubernetes_secret" "storage_credentials" {
  metadata {
    name      = "storage-credentials"
    namespace = var.namespace
  }

  data = {
    accountName = var.storage_account_name
    accountKey  = var.storage_account_key
  }

  type = "Opaque"
}
