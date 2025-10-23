variable "namespace" {
  description = "Kubernetes namespace for NGINX Ingress Controller"
  type        = string
  default     = "ingress-nginx"
}

variable "chart_version" {
  description = "NGINX Ingress Controller Helm chart version"
  type        = string
  default     = "4.8.3"
}

variable "cpu_request" {
  description = "CPU request for NGINX Ingress Controller"
  type        = string
  default     = "100m"
}

variable "cpu_limit" {
  description = "CPU limit for NGINX Ingress Controller"
  type        = string
  default     = "200m"
}

variable "memory_request" {
  description = "Memory request for NGINX Ingress Controller"
  type        = string
  default     = "128Mi"
}

variable "memory_limit" {
  description = "Memory limit for NGINX Ingress Controller"
  type        = string
  default     = "256Mi"
}
