# Variables for Carpeta Ciudadana Module

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "namespace" {
  description = "Kubernetes namespace"
  type        = string
}

variable "chart_path" {
  description = "Path to the Carpeta Ciudadana Helm chart"
  type        = string
  default     = "../../../../deploy/helm/carpeta-ciudadana"
}

variable "chart_version" {
  description = "Carpeta Ciudadana Helm chart version"
  type        = string
  default     = "0.1.0"
}

variable "timeout" {
  description = "Helm chart deployment timeout"
  type        = number
  default     = 600
}

# Global configuration
variable "image_registry" {
  description = "Docker image registry"
  type        = string
  default     = "manuelquistial"
}

variable "image_pull_policy" {
  description = "Docker image pull policy"
  type        = string
  default     = "IfNotPresent"
}

variable "log_level" {
  description = "Application log level"
  type        = string
  default     = "INFO"
}

# Workload Identity
variable "use_workload_identity" {
  description = "Enable Workload Identity"
  type        = bool
  default     = true
}

variable "workload_identity_client_id" {
  description = "Workload Identity Client ID"
  type        = string
}

variable "workload_identity_tenant_id" {
  description = "Workload Identity Tenant ID"
  type        = string
}

# Feature flags
variable "m2m_auth_enabled" {
  description = "Enable M2M authentication"
  type        = bool
  default     = true
}

variable "migrations_enabled" {
  description = "Enable database migrations"
  type        = bool
  default     = true
}

# Resource optimization
variable "resource_optimization_enabled" {
  description = "Enable resource optimization"
  type        = bool
  default     = true
}

variable "max_replicas" {
  description = "Maximum number of replicas"
  type        = number
  default     = 2
}

variable "default_cpu_request" {
  description = "Default CPU request"
  type        = string
  default     = "100m"
}

variable "default_memory_request" {
  description = "Default memory request"
  type        = string
  default     = "128Mi"
}

variable "default_cpu_limit" {
  description = "Default CPU limit"
  type        = string
  default     = "300m"
}

variable "default_memory_limit" {
  description = "Default memory limit"
  type        = string
  default     = "512Mi"
}

# Security configuration
variable "cors_origins" {
  description = "CORS origins"
  type        = string
  default     = "http://localhost:3000,http://localhost:3001"
}

variable "hsts_enabled" {
  description = "Enable HSTS"
  type        = bool
  default     = false
}

variable "csp_enabled" {
  description = "Enable Content Security Policy"
  type        = bool
  default     = true
}

variable "csp_report_uri" {
  description = "CSP report URI"
  type        = string
  default     = ""
}

# Database configuration
variable "database_url" {
  description = "Database connection URL"
  type        = string
  sensitive   = true
}

variable "postgres_uri" {
  description = "PostgreSQL connection URI"
  type        = string
  sensitive   = true
}

variable "m2m_secret_key" {
  description = "M2M secret key"
  type        = string
  sensitive   = true
}

# Azure configuration
variable "azure_storage_account_name" {
  description = "Azure Storage account name"
  type        = string
}

variable "azure_storage_account_key" {
  description = "Azure Storage account key"
  type        = string
  sensitive   = true
}

variable "azure_storage_container_name" {
  description = "Azure Storage container name"
  type        = string
  default     = "documents"
}

# MinTIC configuration
variable "mintic_hub_url" {
  description = "MinTIC Hub URL"
  type        = string
  default     = "https://govcarpeta-apis-4905ff3c005b.herokuapp.com"
}

variable "mintic_operator_id" {
  description = "MinTIC Operator ID"
  type        = string
  default     = "demo-operator"
}

variable "mintic_operator_name" {
  description = "MinTIC Operator Name"
  type        = string
  default     = "Demo Operator"
}

# Cluster configuration
variable "cluster_name" {
  description = "AKS cluster name"
  type        = string
}

variable "cluster_resource_group_name" {
  description = "AKS cluster resource group name"
  type        = string
}

variable "cluster_oidc_issuer_url" {
  description = "AKS cluster OIDC issuer URL"
  type        = string
}

# Database configuration
variable "database_host" {
  description = "Database host"
  type        = string
}

variable "database_name" {
  description = "Database name"
  type        = string
}

variable "database_username" {
  description = "Database username"
  type        = string
  sensitive   = true
}

variable "database_password" {
  description = "Database password"
  type        = string
  sensitive   = true
}

# Redis configuration
variable "redis_host" {
  description = "Redis host"
  type        = string
}

variable "redis_port" {
  description = "Redis port"
  type        = string
}

variable "redis_password" {
  description = "Redis password"
  type        = string
  sensitive   = true
}

# Storage configuration
variable "storage_account_name" {
  description = "Storage account name"
  type        = string
}

variable "storage_account_key" {
  description = "Storage account key"
  type        = string
  sensitive   = true
}

variable "storage_container" {
  description = "Storage container name"
  type        = string
}

# Key Vault configuration
variable "key_vault_name" {
  description = "Key Vault name"
  type        = string
}

variable "key_vault_uri" {
  description = "Key Vault URI"
  type        = string
}

# External Secrets configuration
variable "external_secrets_namespace" {
  description = "External Secrets namespace"
  type        = string
}

variable "cluster_secret_store_name" {
  description = "Cluster Secret Store name"
  type        = string
}

# Ingress configuration
variable "domain_name" {
  description = "Domain name for Ingress"
  type        = string
  default     = ""
}

variable "enable_tls" {
  description = "Enable TLS for Ingress"
  type        = bool
  default     = false
}

# Front Door configuration
variable "frontdoor_enabled" {
  description = "Enable Front Door"
  type        = bool
  default     = false
}

variable "frontdoor_frontend_hostname" {
  description = "Frontend hostname for Front Door"
  type        = string
  default     = ""
}

variable "frontdoor_api_hostname" {
  description = "API hostname for Front Door"
  type        = string
  default     = ""
}

variable "frontdoor_enable_waf" {
  description = "Enable WAF on Front Door"
  type        = bool
  default     = true
}

# Tags
variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
