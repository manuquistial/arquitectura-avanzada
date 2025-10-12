variable "environment" {
  description = "Environment name"
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
  description = "Subnet ID"
  type        = string
}

variable "admin_username" {
  description = "Admin username"
  type        = string
  sensitive   = true
}

variable "admin_password" {
  description = "Admin password"
  type        = string
  sensitive   = true
}

variable "sku_name" {
  description = "PostgreSQL SKU"
  type        = string
  default     = "B_Standard_B1ms"
}

variable "storage_mb" {
  description = "Storage in MB"
  type        = number
  default     = 32768
}

variable "aks_egress_ip" {
  description = "AKS nodepool egress IP address (for firewall rule). Leave empty to skip firewall restriction."
  type        = string
  default     = ""
}

variable "allow_azure_services" {
  description = "Allow Azure services to access PostgreSQL (for backups, monitoring). 0.0.0.0-0.0.0.0 is Azure-only, NOT public internet."
  type        = bool
  default     = false
}

