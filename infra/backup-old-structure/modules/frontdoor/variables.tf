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
