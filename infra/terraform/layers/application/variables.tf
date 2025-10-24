# =============================================================================
# APPLICATION LAYER VARIABLES
# =============================================================================
# Variables específicas para la capa de aplicación
# =============================================================================

# Importar variables compartidas
variable "azure_region" {
  description = "Azure region"
  type        = string
}

variable "azure_subscription_id" {
  description = "Azure subscription ID"
  type        = string
}

variable "security_contact_phone" {
  description = "Security Center contact phone"
  type        = string
}

variable "app_subdomain" {
  description = "Application subdomain"
  type        = string
}

variable "dns_zone_name" {
  description = "DNS zone name"
  type        = string
}

variable "domain_name" {
  description = "Domain name for Ingress"
  type        = string
}

variable "enable_tls" {
  description = "Enable TLS for Ingress"
  type        = bool
  default     = false
}

variable "security_contact_email" {
  description = "Security Center contact email"
  type        = string
}

variable "subnet_cidrs" {
  description = "Subnet CIDR blocks"
  type = object({
    aks = string
    db  = string
  })
}

variable "vnet_cidr" {
  description = "CIDR block for the virtual network"
  type        = string
  default     = "10.0.0.0/16"
}

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

# Front Door Configuration (moved from PLATFORM LAYER)
variable "frontdoor_enabled" {
  description = "Enable Azure Front Door for HTTPS"
  type        = bool
  default     = true
}

variable "frontdoor_frontend_hostname" {
  description = "Frontend hostname for Front Door"
  type        = string
  default     = "135.222.244.88"
}

variable "frontdoor_api_hostname" {
  description = "API hostname for Front Door"
  type        = string
  default     = "135.234.144.31"
}

variable "frontdoor_enable_waf" {
  description = "Enable Web Application Firewall on Front Door"
  type        = bool
  default     = true
}

# OpenSearch Namespace
variable "opensearch_namespace" {
  description = "Namespace where OpenSearch is deployed"
  type        = string
  default     = "opensearch"
}

variable "nextauth_url" {
  description = "NextAuth URL for application secrets"
  type        = string
  default     = "https://app.carpeta-ciudadana.dev"
}

# OpenSearch Configuration - Variables faltantes
variable "opensearch_enabled" {
  description = "Enable OpenSearch deployment"
  type        = bool
  default     = true
}

variable "opensearch_version" {
  description = "OpenSearch Helm chart version"
  type        = string
  default     = "2.11.0"
}

variable "opensearch_replica_count" {
  description = "Number of OpenSearch replicas"
  type        = number
  default     = 1
}

variable "opensearch_storage_size" {
  description = "OpenSearch storage size"
  type        = string
  default     = "10Gi"
}

# cert-manager Configuration - Variables faltantes
variable "cert_manager_version" {
  description = "cert-manager version"
  type        = string
  default     = "v1.13.0"
}

variable "cert_manager_replica_count" {
  description = "Number of cert-manager replicas"
  type        = number
  default     = 1
}
