variable "namespace" {
  description = "Kubernetes namespace for cert-manager"
  type        = string
  default     = "cert-manager"
}

variable "chart_version" {
  description = "cert-manager Helm chart version"
  type        = string
  default     = "v1.13.3"
}

variable "letsencrypt_email" {
  description = "Email address for Let's Encrypt notifications"
  type        = string
}

variable "ingress_class" {
  description = "Ingress class for HTTP-01 challenge"
  type        = string
  default     = "nginx"
}

variable "cpu_request" {
  description = "CPU request for cert-manager controller"
  type        = string
  default     = "100m"
}

variable "cpu_limit" {
  description = "CPU limit for cert-manager controller"
  type        = string
  default     = "200m"
}

variable "memory_request" {
  description = "Memory request for cert-manager controller"
  type        = string
  default     = "128Mi"
}

variable "memory_limit" {
  description = "Memory limit for cert-manager controller"
  type        = string
  default     = "256Mi"
}

