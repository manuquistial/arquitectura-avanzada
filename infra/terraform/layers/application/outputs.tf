# =============================================================================
# APPLICATION LAYER OUTPUTS
# =============================================================================
# Outputs de la capa de aplicación
# =============================================================================

# KEDA Outputs
output "keda_namespace" {
  description = "Namespace where KEDA is deployed"
  value       = module.keda.keda_namespace
}

# cert-manager Outputs
output "cert_manager_namespace" {
  description = "Namespace where cert-manager is deployed"
  value       = module.cert_manager.namespace
}

# OpenSearch Outputs
output "opensearch_namespace" {
  description = "Namespace where OpenSearch is deployed"
  value       = var.opensearch_namespace
}

# Carpeta Ciudadana Outputs
output "carpeta_ciudadana_namespace" {
  description = "Namespace where Carpeta Ciudadana is deployed"
  value       = module.carpeta_ciudadana.namespace
}

# External Secrets Outputs
output "external_secrets_namespace" {
  description = "Namespace where External Secrets Operator is deployed"
  value       = module.external_secrets.external_secrets_namespace
}

output "cluster_secret_store_name" {
  description = "Name of the ClusterSecretStore"
  value       = module.external_secrets.cluster_secret_store_name
}
