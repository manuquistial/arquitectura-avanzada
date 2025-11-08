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

variable "mailjet_enabled" {
  description = "Enable Mailjet secret provisioning"
  type        = bool
  default     = false
}

variable "mailjet_api_key" {
  description = "Mailjet API key"
  type        = string
  default     = ""
  sensitive   = true
}

variable "mailjet_secret_key" {
  description = "Mailjet secret key"
  type        = string
  default     = ""
  sensitive   = true
}

variable "mailjet_from_email" {
  description = "Mailjet sender email"
  type        = string
  default     = ""
}

variable "mailjet_from_name" {
  description = "Mailjet sender name"
  type        = string
  default     = "Carpeta Ciudadana"
}

variable "mailjet_template_id" {
  description = "Mailjet transactional template ID (optional)"
  type        = number
  default     = null
}
