# =============================================================================
# BASE LAYER VARIABLES
# =============================================================================
# Variables específicas para la capa base
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

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "project_name" {
  description = "Project name"
  type        = string
}

variable "vnet_cidr" {
  description = "CIDR block for VNet"
  type        = string
}

variable "subnet_cidrs" {
  description = "Subnet CIDR blocks"
  type = object({
    aks = string
    db  = string
  })
}

variable "dns_zone_name" {
  description = "DNS zone name"
  type        = string
}

variable "app_subdomain" {
  description = "Application subdomain"
  type        = string
}

variable "ingress_ip" {
  description = "Public IP of the ingress controller (leave empty when Front Door + Private Link is used)"
  type        = string
  default     = ""
}

variable "ingress_alias" {
  description = "Private Link Service alias used by Front Door to reach the ingress"
  type        = string
  default     = ""
}

variable "security_contact_email" {
  description = "Security Center contact email"
  type        = string
}

variable "security_contact_phone" {
  description = "Security Center contact phone"
  type        = string
}

variable "domain_name" {
  description = "Domain name for Ingress"
  type        = string
}

variable "enable_tls" {
  description = "Enable TLS for Ingress"
  type        = bool
}
