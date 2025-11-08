variable "dns_zone_name" {
  description = "DNS zone name (e.g., azurewebsites.net)"
  type        = string
}

variable "resource_group_name" {
  description = "Resource group name"
  type        = string
}

variable "app_subdomain" {
  description = "Application subdomain (e.g., carpeta-dev)"
  type        = string
}

variable "ingress_ip" {
  description = "Ingress controller public IP address (leave empty when using Private Link)"
  type        = string
  default     = ""
}

variable "ingress_alias" {
  description = "Private Link Service alias used by Front Door (e.g., pls-alias.privatelinkservice)"
  type        = string
  default     = ""
}

variable "tags" {
  description = "Tags for DNS resources"
  type        = map(string)
  default     = {}
}
