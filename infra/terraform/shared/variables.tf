# =============================================================================
# SHARED VARIABLES
# =============================================================================
# Variables compartidas entre todas las capas
# =============================================================================

# Azure Configuration
variable "azure_region" {
  description = "Azure region"
  type        = string
  default     = "westus2"
}

variable "azure_subscription_id" {
  description = "Azure subscription ID"
  type        = string
  default     = null
}

variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "carpeta-ciudadana"
}

# Security Configuration
variable "security_contact_email" {
  description = "Security Center contact email"
  type        = string
  default     = "security@carpeta-ciudadana.com"
}

variable "security_contact_phone" {
  description = "Security Center contact phone"
  type        = string
  default     = "+1-555-0123"
}

# Network Configuration
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

# DNS Configuration
variable "dns_zone_name" {
  description = "DNS zone name (e.g., carpeta-ciudadana.dev)"
  type        = string
  default     = "carpeta-ciudadana.dev"
}

variable "app_subdomain" {
  description = "Application subdomain (e.g., app)"
  type        = string
  default     = "app"
}

# Domain Configuration
variable "domain_name" {
  description = "Domain name for Ingress (optional)"
  type        = string
  default     = ""
}

variable "enable_tls" {
  description = "Enable TLS for Ingress (requires domain)"
  type        = bool
  default     = false
}

