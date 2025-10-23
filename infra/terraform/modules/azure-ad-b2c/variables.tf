# Azure AD B2C Module Variables

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
}

variable "b2c_tenant_name" {
  description = "Azure AD B2C tenant name (e.g., carpetaciudadana)"
  type        = string
  default     = "carpetaciudadana"
}

variable "redirect_uris" {
  description = "Redirect URIs for the B2C application"
  type        = list(string)
  default = [
    "http://localhost:3000/api/auth/callback/azure-ad-b2c",
    "https://carpeta-ciudadana.com/api/auth/callback/azure-ad-b2c"
  ]
}

variable "logout_redirect_uri" {
  description = "Logout redirect URI"
  type        = string
  default     = "http://localhost:3000"
}

variable "enable_implicit_flow" {
  description = "Enable implicit flow for B2C"
  type        = bool
  default     = true
}

variable "enable_authorization_code_flow" {
  description = "Enable authorization code flow for B2C"
  type        = bool
  default     = true
}

variable "enable_client_credentials_flow" {
  description = "Enable client credentials flow for B2C"
  type        = bool
  default     = true
}

variable "user_flow_name" {
  description = "B2C user flow name"
  type        = string
  default     = "B2C_1_signupsignin"
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default = {
    Project     = "CarpetaCiudadana"
    Environment = "production"
    ManagedBy   = "Terraform"
  }
}
