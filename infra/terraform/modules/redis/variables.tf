variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
}

variable "namespace" {
  description = "Kubernetes namespace for Redis"
  type        = string
  default     = "carpeta-ciudadana-dev"
}
