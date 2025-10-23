output "postgresql_secret_name" {
  description = "PostgreSQL secret name"
  value       = kubernetes_secret.postgresql_secret.metadata[0].name
}

output "azure_storage_secret_name" {
  description = "Azure Storage secret name"
  value       = var.azure_storage_enabled ? kubernetes_secret.azure_storage_secret[0].metadata[0].name : null
}

output "servicebus_secret_name" {
  description = "Service Bus secret name"
  value       = var.servicebus_enabled ? kubernetes_secret.servicebus_secret[0].metadata[0].name : null
}

output "redis_secret_name" {
  description = "Redis secret name"
  value       = var.redis_enabled ? kubernetes_secret.redis_secret[0].metadata[0].name : null
}

output "azure_b2c_secret_name" {
  description = "Azure AD B2C secret name"
  value       = var.azure_b2c_enabled ? kubernetes_secret.azure_b2c_secret[0].metadata[0].name : null
}

output "m2m_secret_name" {
  description = "M2M secret name"
  value       = kubernetes_secret.m2m_secret.metadata[0].name
}
