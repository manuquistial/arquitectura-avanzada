variable "namespace" {
  description = "Kubernetes namespace for secrets"
  type        = string
  default     = "carpeta-ciudadana-production"
}

variable "namespace_dependency" {
  description = "Dependency to ensure namespace is created before secrets"
  type        = any
  default     = null
}

# PostgreSQL variables
variable "postgresql_fqdn" {
  description = "PostgreSQL FQDN"
  type        = string
}

variable "postgresql_username" {
  description = "PostgreSQL username"
  type        = string
  sensitive   = true
}

variable "postgresql_password" {
  description = "PostgreSQL password"
  type        = string
  sensitive   = true
}

variable "postgresql_database" {
  description = "PostgreSQL database name"
  type        = string
  default     = "carpeta_ciudadana"
}

# Azure Storage variables
variable "azure_storage_enabled" {
  description = "Enable Azure Storage secret"
  type        = bool
  default     = true
}

variable "azure_storage_account_name" {
  description = "Azure Storage account name"
  type        = string
  default     = ""
}

variable "azure_storage_account_key" {
  description = "Azure Storage account key"
  type        = string
  sensitive   = true
  default     = ""
}

variable "azure_storage_container_name" {
  description = "Azure Storage container name"
  type        = string
  default     = "documents"
}

# Service Bus variables
variable "servicebus_enabled" {
  description = "Enable Service Bus secret"
  type        = bool
  default     = true
}

variable "servicebus_connection_string" {
  description = "Service Bus connection string"
  type        = string
  sensitive   = true
  default     = ""
}

# Redis variables
variable "redis_enabled" {
  description = "Enable Redis secret"
  type        = bool
  default     = true
}

variable "redis_host" {
  description = "Redis host"
  type        = string
  default     = ""
}

variable "redis_port" {
  description = "Redis port"
  type        = string
  default     = "6380"
}

variable "redis_password" {
  description = "Redis password"
  type        = string
  sensitive   = true
  default     = ""
}

variable "redis_ssl" {
  description = "Redis SSL enabled"
  type        = string
  default     = "true"
}

# Azure AD B2C variables
variable "azure_b2c_enabled" {
  description = "Enable Azure AD B2C secret"
  type        = bool
  default     = true
}

variable "azure_b2c_tenant_id" {
  description = "Azure AD B2C tenant ID"
  type        = string
  sensitive   = true
  default     = ""
}

variable "azure_b2c_client_id" {
  description = "Azure AD B2C client ID"
  type        = string
  sensitive   = true
  default     = ""
}

variable "azure_b2c_client_secret" {
  description = "Azure AD B2C client secret"
  type        = string
  sensitive   = true
  default     = ""
}

# M2M Authentication variables
variable "m2m_secret_key" {
  description = "M2M authentication secret key"
  type        = string
  sensitive   = true
}
