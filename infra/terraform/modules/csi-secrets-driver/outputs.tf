/**
 * CSI Secrets Driver Module Outputs
 */

output "csi_driver_name" {
  description = "CSI Secrets Store driver Helm release name"
  value       = helm_release.secrets_store_csi_driver.name
}

output "azure_provider_name" {
  description = "Azure Key Vault Provider Helm release name"
  value       = helm_release.azure_keyvault_provider.name
}

output "namespace" {
  description = "Namespace where CSI driver is installed"
  value       = var.namespace
}

