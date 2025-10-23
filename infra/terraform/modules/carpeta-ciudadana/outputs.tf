# Carpeta Ciudadana Module Outputs

output "namespace" {
  description = "Kubernetes namespace where the application is deployed"
  value       = var.namespace
}

output "kubernetes_namespace_app" {
  description = "Kubernetes namespace resource for dependency management"
  value       = var.create_namespace ? kubernetes_namespace.app[0] : null
}

output "helm_release_name" {
  description = "Helm release name"
  value       = helm_release.carpeta_ciudadana.name
}

output "helm_release_version" {
  description = "Helm release version"
  value       = helm_release.carpeta_ciudadana.version
}

output "helm_release_status" {
  description = "Helm release status"
  value       = helm_release.carpeta_ciudadana.status
}

# TEMPORARILY COMMENTED - Let Helm manage secrets
# output "database_secret_name" {
#   description = "Name of the database secret"
#   value       = kubernetes_secret.database.metadata[0].name
# }

# output "m2m_secret_name" {
#   description = "Name of the M2M authentication secret"
#   value       = kubernetes_secret.m2m_auth.metadata[0].name
# }

# output "servicebus_secret_name" {
#   description = "Name of the Service Bus secret (if enabled)"
#   value       = var.servicebus_enabled ? kubernetes_secret.servicebus[0].metadata[0].name : null
# }

# output "azure_storage_secret_name" {
#   description = "Name of the Azure Storage secret"
#   value       = kubernetes_secret.azure_storage.metadata[0].name
# }

# output "azure_b2c_secret_name" {
#   description = "Name of the Azure B2C secret (if enabled)"
#   value       = var.azure_b2c_enabled ? kubernetes_secret.azure_b2c[0].metadata[0].name : null
# }
