# =============================================================================
# EXTERNAL SECRETS OPERATOR OUTPUTS
# =============================================================================

output "external_secrets_namespace" {
  description = "Namespace where External Secrets Operator is deployed"
  value       = var.namespace
}

output "cluster_secret_store_name" {
  description = "Name of the ClusterSecretStore"
  value       = "azure-keyvault"
}


