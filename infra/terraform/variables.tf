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

# AKS - Advanced Configuration
variable "aks_node_count" {
  description = "DEPRECATED: Number of AKS nodes (use aks_system_node_count)"
  type        = number
  default     = 1
}

variable "aks_vm_size" {
  description = "DEPRECATED: AKS node VM size (use aks_system_vm_size)"
  type        = string
  default     = "Standard_B2s"
}

# Kubernetes version
variable "aks_kubernetes_version" {
  description = "Kubernetes version"
  type        = string
  default     = "1.28"
}

variable "aks_automatic_upgrade" {
  description = "Automatic upgrade channel (patch, stable, rapid, node-image, none)"
  type        = string
  default     = "patch"
}

# Cluster configuration
variable "aks_private_cluster" {
  description = "Enable private cluster (API server not public)"
  type        = bool
  default     = false  # true for production
}

variable "aks_sku_tier" {
  description = "AKS SKU tier (Free, Standard)"
  type        = string
  default     = "Free"  # Standard for production (99.95% SLA)
}

variable "aks_authorized_ip_ranges" {
  description = "Authorized IP ranges for API server"
  type        = list(string)
  default     = []
}

variable "aks_admin_groups" {
  description = "Azure AD group object IDs for cluster admins"
  type        = list(string)
  default     = []
}

# Availability zones (multi-AZ)
variable "aks_availability_zones" {
  description = "Availability zones for node pools"
  type        = list(string)
  default     = ["1", "2", "3"]
}

# System node pool (K8s controllers)
variable "aks_system_vm_size" {
  description = "VM size for system node pool"
  type        = string
  default     = "Standard_B2s"
}

variable "aks_system_node_count" {
  description = "System node count (if autoscaling disabled)"
  type        = number
  default     = 1
}

variable "aks_system_node_min" {
  description = "Minimum system nodes (autoscaling)"
  type        = number
  default     = 1
}

variable "aks_system_node_max" {
  description = "Maximum system nodes (autoscaling)"
  type        = number
  default     = 3
}

# User node pool (applications)
variable "aks_user_vm_size" {
  description = "VM size for user node pool"
  type        = string
  default     = "Standard_D2s_v3"
}

variable "aks_user_node_min" {
  description = "Minimum user nodes"
  type        = number
  default     = 2
}

variable "aks_user_node_max" {
  description = "Maximum user nodes"
  type        = number
  default     = 10
}

# Spot node pool (KEDA workers)
variable "aks_enable_spot" {
  description = "Enable spot node pool"
  type        = bool
  default     = true
}

variable "aks_spot_vm_size" {
  description = "VM size for spot node pool"
  type        = string
  default     = "Standard_D2s_v3"
}

variable "aks_spot_node_min" {
  description = "Minimum spot nodes"
  type        = number
  default     = 0  # Can scale to zero
}

variable "aks_spot_node_max" {
  description = "Maximum spot nodes"
  type        = number
  default     = 10
}

variable "aks_spot_max_price" {
  description = "Max price for spot instances (-1 = regular price)"
  type        = number
  default     = -1
}

# Auto-scaling
variable "aks_enable_autoscaling" {
  description = "Enable cluster autoscaler"
  type        = bool
  default     = true
}

# Network
variable "aks_service_cidr" {
  description = "Kubernetes service CIDR"
  type        = string
  default     = "10.1.0.0/16"
}

variable "aks_dns_service_ip" {
  description = "Kubernetes DNS service IP"
  type        = string
  default     = "10.1.0.10"
}

variable "aks_outbound_type" {
  description = "Outbound type (loadBalancer, userDefinedRouting)"
  type        = string
  default     = "loadBalancer"
}

# Maintenance window
variable "aks_maintenance_day" {
  description = "Maintenance window day"
  type        = string
  default     = "Sunday"
}

variable "aks_maintenance_hours" {
  description = "Maintenance window hours"
  type        = list(number)
  default     = [2, 3, 4]
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

# Key Vault
variable "keyvault_sku" {
  description = "Key Vault SKU (standard or premium)"
  type        = string
  default     = "standard"
}

variable "keyvault_enable_public_access" {
  description = "Enable public network access to Key Vault"
  type        = bool
  default     = true  # false for production with private endpoint
}

variable "keyvault_purge_protection" {
  description = "Enable purge protection (prevents permanent deletion)"
  type        = bool
  default     = false  # true for production
}

variable "keyvault_soft_delete_days" {
  description = "Soft delete retention in days (7-90)"
  type        = number
  default     = 7
}

# M2M Authentication
variable "m2m_secret_key" {
  description = "M2M authentication secret key (generate with: openssl rand -hex 32)"
  type        = string
  sensitive   = true
  default     = ""
}

# Redis
variable "redis_password" {
  description = "Redis password (optional)"
  type        = string
  sensitive   = true
  default     = ""
}

# Azure AD B2C
variable "azure_b2c_tenant_id" {
  description = "Azure AD B2C tenant ID"
  type        = string
  sensitive   = true
  default     = ""
}

variable "azure_b2c_client_id" {
  description = "Azure AD B2C client ID"
  type        = string
  sensitive   = true
  default     = ""
}

variable "azure_b2c_client_secret" {
  description = "Azure AD B2C client secret"
  type        = string
  sensitive   = true
  default     = ""
}

# CSI Secrets Store Driver
variable "csi_secrets_namespace" {
  description = "Namespace for CSI Secrets Store Driver"
  type        = string
  default     = "kube-system"
}

variable "csi_enable_rotation" {
  description = "Enable automatic secret rotation"
  type        = bool
  default     = true
}

variable "csi_rotation_interval" {
  description = "Secret rotation poll interval"
  type        = string
  default     = "2m"
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

