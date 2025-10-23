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

# =============================================================================
# CARPETA CIUDADANA OUTPUTS - MOVED TO SEPARATE LAYER
# =============================================================================
# Carpeta Ciudadana outputs have been moved to layers/carpeta-ciudadana/
# =============================================================================

# External Secrets Outputs
output "external_secrets_namespace" {
  description = "Namespace where External Secrets Operator is deployed"
  value       = data.terraform_remote_state.external_secrets.outputs.external_secrets_namespace
}

output "cluster_secret_store_name" {
  description = "Name of the ClusterSecretStore"
  value       = data.terraform_remote_state.external_secrets.outputs.cluster_secret_store_name
}

# Front Door Outputs (moved from PLATFORM LAYER)
output "frontdoor_id" {
  description = "ID of the Front Door"
  value       = var.frontdoor_enabled ? module.frontdoor[0].frontdoor_profile_id : null
}

output "frontdoor_endpoint" {
  description = "Front Door endpoint"
  value       = var.frontdoor_enabled ? module.frontdoor[0].frontdoor_endpoint_hostname : null
}
