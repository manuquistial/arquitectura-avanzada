variable "environment" {
  description = "Environment name"
  type        = string
}

variable "cluster_name" {
  description = "AKS cluster name"
  type        = string
}

variable "resource_group_name" {
  description = "Resource group name"
  type        = string
}

variable "location" {
  description = "Azure location"
  type        = string
}

variable "subnet_id" {
  description = "Subnet ID for AKS"
  type        = string
}

# Kubernetes version
variable "kubernetes_version" {
  description = "Kubernetes version"
  type        = string
  default     = "1.28"
}

variable "automatic_channel_upgrade" {
  description = "Auto-upgrade channel (patch, stable, rapid, node-image, none)"
  type        = string
  default     = "patch"
}

# Cluster configuration
variable "private_cluster_enabled" {
  description = "Enable private cluster (API server not public)"
  type        = bool
  default     = false
}

variable "sku_tier" {
  description = "AKS SKU tier (Free, Standard)"
  type        = string
  default     = "Free" # Standard for production (99.95% SLA)
}

variable "authorized_ip_ranges" {
  description = "Authorized IP ranges for API server access"
  type        = list(string)
  default     = [] # Empty = allow all
}

variable "admin_group_object_ids" {
  description = "Azure AD group object IDs for cluster admins"
  type        = list(string)
  default     = []
}

# Availability zones
variable "availability_zones" {
  description = "Availability zones for node pools (multi-AZ HA)"
  type        = list(string)
  default     = ["1", "2", "3"]
}

# System node pool (default pool - for K8s controllers)
variable "system_vm_size" {
  description = "VM size for system node pool"
  type        = string
  default     = "Standard_D4s_v3"
}

variable "system_node_count" {
  description = "Number of system nodes (if auto-scaling disabled)"
  type        = number
  default     = 1
}

variable "system_node_min" {
  description = "Minimum system nodes (auto-scaling)"
  type        = number
  default     = 1
}

variable "system_node_max" {
  description = "Maximum system nodes (auto-scaling)"
  type        = number
  default     = 3
}

# User node pool (for application workloads)
variable "user_vm_size" {
  description = "VM size for user node pool"
  type        = string
  default     = "Standard_D4s_v3"
}

variable "user_node_min" {
  description = "Minimum user nodes"
  type        = number
  default     = 2
}

variable "user_node_max" {
  description = "Maximum user nodes"
  type        = number
  default     = 10
}

# Spot node pool (for KEDA workers)
variable "enable_spot_nodepool" {
  description = "Enable spot node pool for workers (70% cost savings)"
  type        = bool
  default     = true
}

variable "spot_vm_size" {
  description = "VM size for spot node pool"
  type        = string
  default     = "Standard_D4s_v3"
}

variable "spot_node_min" {
  description = "Minimum spot nodes"
  type        = number
  default     = 0 # Can scale to zero
}

variable "spot_node_max" {
  description = "Maximum spot nodes"
  type        = number
  default     = 10
}

variable "spot_max_price" {
  description = "Maximum price for spot instances (-1 = regular price)"
  type        = number
  default     = -1
}

# Auto-scaling
variable "enable_auto_scaling" {
  description = "Enable cluster autoscaler"
  type        = bool
  default     = true
}

# Network
variable "service_cidr" {
  description = "Kubernetes service CIDR"
  type        = string
  default     = "10.1.0.0/16"
}

variable "dns_service_ip" {
  description = "Kubernetes DNS service IP"
  type        = string
  default     = "10.1.0.10"
}

variable "outbound_type" {
  description = "Outbound network type (loadBalancer, userDefinedRouting)"
  type        = string
  default     = "loadBalancer"
}

# Maintenance window
variable "maintenance_window_day" {
  description = "Maintenance window day (Sunday, Monday, etc.)"
  type        = string
  default     = "Sunday"
}

variable "maintenance_window_hours" {
  description = "Maintenance window hours (0-23)"
  type        = list(number)
  default     = [2, 3, 4] # 2am-5am
}

# Legacy variables (for backward compatibility)
variable "node_count" {
  description = "DEPRECATED: Use system_node_count instead"
  type        = number
  default     = 1
}

variable "vm_size" {
  description = "DEPRECATED: Use system_vm_size instead"
  type        = string
  default     = "Standard_D4s_v3"
}

# Azure AD
variable "tenant_id" {
  description = "Azure AD tenant ID"
  type        = string
}
