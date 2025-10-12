/**
 * CSI Secrets Driver Module Variables
 */

variable "namespace" {
  description = "Kubernetes namespace for CSI driver"
  type        = string
  default     = "kube-system"
}

variable "csi_driver_version" {
  description = "Secrets Store CSI Driver version"
  type        = string
  default     = "1.4.0"
}

variable "azure_provider_version" {
  description = "Azure Key Vault Provider version"
  type        = string
  default     = "1.5.0"
}

variable "enable_secret_rotation" {
  description = "Enable automatic secret rotation"
  type        = bool
  default     = true
}

variable "rotation_poll_interval" {
  description = "Secret rotation poll interval"
  type        = string
  default     = "2m"
}

