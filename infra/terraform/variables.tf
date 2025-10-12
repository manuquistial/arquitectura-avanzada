variable "azure_region" {
  description = "Azure region"
  type        = string
  default     = "eastus"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "carpeta-ciudadana"
}

# VNet
variable "vnet_cidr" {
  description = "CIDR block for VNet"
  type        = string
  default     = "10.0.0.0/16"
}

variable "subnet_cidrs" {
  description = "Subnet CIDR blocks"
  type = object({
    aks = string
    db  = string
  })
  default = {
    aks = "10.0.1.0/24"
    db  = "10.0.2.0/24"
  }
}

# AKS
variable "aks_node_count" {
  description = "Number of AKS nodes"
  type        = number
  default     = 1
}

variable "aks_vm_size" {
  description = "AKS node VM size"
  type        = string
  default     = "Standard_B2s"
}

# PostgreSQL
variable "db_admin_username" {
  description = "Database admin username"
  type        = string
  sensitive   = true
}

variable "db_admin_password" {
  description = "Database admin password"
  type        = string
  sensitive   = true
}

variable "db_sku_name" {
  description = "PostgreSQL SKU"
  type        = string
  default     = "B_Standard_B1ms"
}

variable "db_storage_mb" {
  description = "PostgreSQL storage in MB"
  type        = number
  default     = 32768
}

variable "db_enable_public_access" {
  description = "Enable public network access to PostgreSQL (true for dev, false for prod with private endpoint)"
  type        = bool
  default     = true
}

variable "db_aks_egress_ip" {
  description = "AKS nodepool egress IP for PostgreSQL firewall (leave empty to query dynamically)"
  type        = string
  default     = ""
}

variable "db_allow_azure_services" {
  description = "Allow Azure services to access PostgreSQL (for backups, monitoring)"
  type        = bool
  default     = false
}

# Cognitive Search
variable "search_sku" {
  description = "Azure Cognitive Search SKU"
  type        = string
  default     = "basic"
}

# Service Bus
variable "servicebus_sku" {
  description = "Service Bus SKU"
  type        = string
  default     = "Basic"
}

# Azure AD B2C
variable "adb2c_domain_name" {
  description = "Azure AD B2C domain name"
  type        = string
  default     = "carpetaciudadana"
}

# Container Registry
variable "acr_sku" {
  description = "ACR SKU"
  type        = string
  default     = "Basic"
}

# cert-manager
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

variable "enable_tls" {
  description = "Enable TLS for Ingress (requires domain)"
  type        = bool
  default     = false
}

variable "domain_name" {
  description = "Domain name for Ingress (optional)"
  type        = string
  default     = ""
}

# Observability
variable "observability_namespace" {
  description = "Kubernetes namespace for observability stack"
  type        = string
  default     = "observability"
}

variable "otel_chart_version" {
  description = "OpenTelemetry Collector chart version"
  type        = string
  default     = "0.78.0"
}

variable "otel_replicas" {
  description = "OpenTelemetry Collector replicas"
  type        = number
  default     = 2
}

variable "prometheus_chart_version" {
  description = "Prometheus chart version"
  type        = string
  default     = "25.8.0"
}

variable "prometheus_retention" {
  description = "Prometheus data retention"
  type        = string
  default     = "15d"
}

# KEDA (Kubernetes Event-Driven Autoscaling)
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

variable "prometheus_storage_size" {
  description = "Prometheus storage size"
  type        = string
  default     = "10Gi"
}

# OpenSearch
variable "opensearch_namespace" {
  description = "Kubernetes namespace for OpenSearch"
  type        = string
  default     = "search"
}

variable "opensearch_chart_version" {
  description = "OpenSearch Helm chart version"
  type        = string
  default     = "2.17.0"
}

variable "opensearch_storage_size" {
  description = "OpenSearch PVC storage size"
  type        = string
  default     = "8Gi"
}

variable "opensearch_storage_class" {
  description = "Storage class for OpenSearch PVC"
  type        = string
  default     = "managed-premium"
}

variable "opensearch_memory_request" {
  description = "OpenSearch memory request"
  type        = string
  default     = "1Gi"
}

variable "opensearch_memory_limit" {
  description = "OpenSearch memory limit"
  type        = string
  default     = "2Gi"
}

variable "opensearch_cpu_request" {
  description = "OpenSearch CPU request"
  type        = string
  default     = "500m"
}

variable "opensearch_cpu_limit" {
  description = "OpenSearch CPU limit"
  type        = string
  default     = "1000m"
}

variable "opensearch_heap_size" {
  description = "OpenSearch Java heap size"
  type        = string
  default     = "1g"
}

variable "opensearch_username" {
  description = "OpenSearch admin username"
  type        = string
  default     = "admin"
  sensitive   = true
}

variable "opensearch_password" {
  description = "OpenSearch admin password"
  type        = string
  sensitive   = true
}

variable "opensearch_enable_dashboards" {
  description = "Enable OpenSearch Dashboards"
  type        = bool
  default     = true
}

