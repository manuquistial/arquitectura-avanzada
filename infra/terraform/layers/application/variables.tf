# =============================================================================
# APPLICATION LAYER VARIABLES
# =============================================================================
# Variables específicas para la capa de aplicación
# =============================================================================

# Importar variables compartidas
variable "environment" {
  description = "Environment name"
  type        = string
}

variable "project_name" {
  description = "Project name"
  type        = string
}

# KEDA Configuration
variable "keda_version" {
  description = "KEDA Helm chart version"
  type        = string
  default     = "2.13.0"
}

variable "keda_namespace" {
  description = "Kubernetes namespace for KEDA"
  type        = string
  default     = "keda-system"
}

variable "keda_replica_count" {
  description = "Number of replicas for KEDA operator (HA)"
  type        = number
  default     = 2
}

# cert-manager Configuration
variable "cert_manager_namespace" {
  description = "Kubernetes namespace for cert-manager"
  type        = string
  default     = "cert-manager"
}

variable "cert_manager_chart_version" {
  description = "cert-manager Helm chart version"
  type        = string
  default     = "v1.13.3"
}

variable "letsencrypt_email" {
  description = "Email address for Let's Encrypt notifications"
  type        = string
}

variable "cert_manager_ingress_class" {
  description = "Ingress class for cert-manager HTTP-01 challenge"
  type        = string
  default     = "nginx"
}

variable "cert_manager_cpu_request" {
  description = "cert-manager CPU request"
  type        = string
  default     = "100m"
}

variable "cert_manager_cpu_limit" {
  description = "cert-manager CPU limit"
  type        = string
  default     = "200m"
}

variable "cert_manager_memory_request" {
  description = "cert-manager memory request"
  type        = string
  default     = "128Mi"
}

variable "cert_manager_memory_limit" {
  description = "cert-manager memory limit"
  type        = string
  default     = "256Mi"
}

# OpenSearch Configuration
variable "opensearch_username" {
  description = "OpenSearch admin username"
  type        = string
  default     = "admin"
}

variable "opensearch_password" {
  description = "OpenSearch admin password"
  type        = string
  default     = "admin123"
  sensitive   = true
}

# External Secrets Configuration
variable "external_secrets_namespace" {
  description = "Namespace where External Secrets Operator is deployed"
  type        = string
  default     = "external-secrets-system"
}

variable "external_secrets_version" {
  description = "External Secrets Operator Helm chart version"
  type        = string
  default     = "0.9.11"
}

# M2M Authentication
variable "m2m_secret_key" {
  description = "M2M authentication secret key"
  type        = string
  sensitive   = true
  default     = ""
}

# OpenSearch Namespace
variable "opensearch_namespace" {
  description = "Namespace where OpenSearch is deployed"
  type        = string
  default     = "opensearch"
}
