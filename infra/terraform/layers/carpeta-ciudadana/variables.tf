# Variables for Carpeta Ciudadana Layer

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "namespace" {
  description = "Kubernetes namespace for Carpeta Ciudadana"
  type        = string
  default     = "carpeta-ciudadana"
}

variable "m2m_secret_key" {
  description = "M2M secret key"
  type        = string
  sensitive   = true
}

variable "domain_name" {
  description = "Domain name for Ingress"
  type        = string
  default     = ""
}

variable "enable_tls" {
  description = "Enable TLS for Ingress"
  type        = bool
  default     = false
}

variable "frontdoor_enabled" {
  description = "Enable Azure Front Door for HTTPS"
  type        = bool
  default     = true
}

variable "frontdoor_frontend_hostname" {
  description = "Frontend hostname for Front Door"
  type        = string
  default     = ""
}

variable "frontdoor_api_hostname" {
  description = "API hostname for Front Door"
  type        = string
  default     = ""
}

variable "frontdoor_enable_waf" {
  description = "Enable Web Application Firewall on Front Door"
  type        = bool
  default     = true
}

variable "azure_subscription_id" {
  description = "Azure subscription ID"
  type        = string
}

variable "cors_origins" {
  description = "CORS allowed origins"
  type        = string
  default     = "[\"http://localhost:3000\",\"http://carpeta-ciudadana-frontend:80\",\"*\"]"
}

# Frontend configuration
variable "frontend_url" {
  description = "Frontend URL for NextAuth configuration"
  type        = string
  default     = ""
}

variable "nextauth_secret" {
  description = "NextAuth secret for authentication"
  type        = string
  sensitive   = true
  default     = ""
}
