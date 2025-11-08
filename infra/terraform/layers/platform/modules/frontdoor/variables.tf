variable "environment" {
  description = "Environment name (e.g., production, staging)"
  type        = string
}

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "frontend_hostname" {
  description = "Hostname for the frontend service"
  type        = string
  default     = "135.222.244.88"
}

variable "api_hostname" {
  description = "Hostname for the API gateway service"
  type        = string
  default     = "135.234.144.31"
}

variable "enable_waf" {
  description = "Enable Web Application Firewall (WAF)"
  type        = bool
  default     = true
}

variable "sku_name" {
  description = "Azure Front Door SKU (e.g., Standard_AzureFrontDoor, Premium_AzureFrontDoor)"
  type        = string
  default     = "Premium_AzureFrontDoor"
}

variable "private_link_enabled" {
  description = "Enable Private Link integration for origins"
  type        = bool
  default     = false
}

variable "private_link_location" {
  description = "Location of the Private Link target"
  type        = string
  default     = ""
}

variable "private_link_target_id" {
  description = "Resource ID of the Private Link target (Private Link Service)"
  type        = string
  default     = ""
}

variable "private_link_request_message" {
  description = "Request message to display when approving Private Link connections"
  type        = string
  default     = "Azure Front Door access request"
}

variable "private_link_target_type" {
  description = "Private Link target type (e.g., sites, web, blob, Gateway)"
  type        = string
  default     = "sites"
}

variable "frontend_origin_group_name" {
  description = "Name of the Front Door origin group for the frontend origin"
  type        = string
  default     = ""
}

variable "api_origin_group_name" {
  description = "Name of the Front Door origin group for the API origin"
  type        = string
  default     = ""
}

variable "custom_domain_names" {
  description = "List of custom domain names for the Front Door"
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}

# Opcional: nombre explícito del Front Door Profile.
# Si se deja vacío, se usará "${var.environment}-carpeta-afd-<sufijo>".
variable "profile_name" {
  description = "Optional explicit name for the Front Door Profile"
  type        = string
  default     = ""
}
