# =============================================================================
# APPLICATION SECRETS MODULE VARIABLES
# =============================================================================

variable "key_vault_id" {
  description = "ID of the Key Vault where secrets will be stored"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "application_secrets" {
  description = "Additional application secrets to create"
  type        = map(string)
  default     = {}
}

variable "nextauth_url" {
  description = "NextAuth URL for the application"
  type        = string
  default     = "https://app.carpeta-ciudadana.dev"
}
