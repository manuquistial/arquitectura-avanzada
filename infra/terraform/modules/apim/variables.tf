variable "environment" {
  description = "Environment name"
  type        = string
}

variable "location" {
  description = "Azure region"
  type        = string
}

variable "resource_group_name" {
  description = "Resource group name"
  type        = string
}

variable "publisher_name" {
  description = "Publisher name for API Management"
  type        = string
  default     = "Carpeta Ciudadana"
}

variable "publisher_email" {
  description = "Publisher email for API Management"
  type        = string
}

variable "sku_name" {
  description = "API Management SKU"
  type        = string
  default     = "Developer_1"  # Free tier for development
}

variable "subnet_id" {
  description = "Subnet ID for API Management"
  type        = string
}

variable "virtual_network_id" {
  description = "Virtual network ID"
  type        = string
}

variable "private_endpoint_subnet_id" {
  description = "Private endpoint subnet ID"
  type        = string
}

# gateway_service_url removed - APIM routes directly to microservices
# variable "gateway_service_url" - REMOVED

variable "custom_domain_name" {
  description = "Custom domain name for API Management"
  type        = string
  default     = ""
}

variable "key_vault_certificate_id" {
  description = "Key Vault certificate ID for custom domain"
  type        = string
  default     = ""
}

# Monitoring and Logging
variable "eventhub_name" {
  description = "Event Hub name for logging"
  type        = string
  default     = "carpeta-ciudadana-logs"
}

variable "eventhub_connection_string" {
  description = "Event Hub connection string"
  type        = string
  default     = ""
  sensitive   = true
}

variable "log_analytics_workspace_id" {
  description = "Log Analytics workspace ID for diagnostics"
  type        = string
  default     = ""
}

# Authentication Configuration
variable "tenant_id" {
  description = "Azure AD tenant ID"
  type        = string
  default     = ""
  sensitive   = true
}

variable "client_id" {
  description = "Azure AD client ID"
  type        = string
  default     = ""
  sensitive   = true
}

variable "apim_name" {
  description = "API Management instance name"
  type        = string
  default     = "carpeta-ciudadana-apim"
}

variable "enable_private_endpoint" {
  description = "Enable private endpoint for API Management"
  type        = bool
  default     = false
}

variable "vnet_id" {
  description = "Virtual network ID"
  type        = string
  default     = ""
}
