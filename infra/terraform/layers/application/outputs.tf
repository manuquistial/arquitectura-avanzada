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

# Front Door Outputs - MOVED TO PLATFORM LAYER
# Front Door es infraestructura de red y se gestiona en PLATFORM layer
# Acceder a través de: data.terraform_remote_state.platform.outputs.frontdoor_*

output "nextauth_url" {
  description = "NextAuth URL for application secrets"
  value       = var.nextauth_url
}
