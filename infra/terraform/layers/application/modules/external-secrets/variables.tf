# =============================================================================
# EXTERNAL SECRETS OPERATOR VARIABLES
# =============================================================================

variable "namespace" {
  description = "Kubernetes namespace for External Secrets Operator"
  type        = string
  default     = "external-secrets-system"
}

variable "chart_version" {
  description = "External Secrets Operator Helm chart version"
  type        = string
  default     = "0.9.11"
}

variable "keyvault_name" {
  description = "Name of the Azure Key Vault"
  type        = string
}

variable "keyvault_id" {
  description = "ID of the Azure Key Vault"
  type        = string
}

variable "aks_managed_identity_principal_id" {
  description = "Principal ID of the AKS Managed Identity"
  type        = string
}

variable "aks_oidc_issuer_url" {
  description = "OIDC issuer URL of the AKS cluster"
  type        = string
}
