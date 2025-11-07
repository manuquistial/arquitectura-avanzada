variable "environment" {
  description = "Environment name"
  type        = string
}

variable "location" {
  description = "Azure region"
  type        = string
}

variable "resource_group_name" {
  description = "Resource group name"
  type        = string
}

variable "sku" {
  description = "Service Bus SKU (Basic or Standard)"
  type        = string
  default     = "Standard"
}

variable "capacity" {
  description = "Service Bus capacity (only for Standard SKU)"
  type        = number
  default     = 0
}

variable "public_network_access_enabled" {
  description = "Enable public network access"
  type        = bool
  default     = true
}

variable "minimum_tls_version" {
  description = "Minimum TLS version"
  type        = string
  default     = "1.2"
}

variable "key_vault_id" {
  description = "Key Vault ID for secret management"
  type        = string
  default     = ""
}

variable "citizen_events_queue_name" {
  description = "Service Bus queue name for citizen events"
  type        = string
  default     = "citizen-events"
}

variable "document_events_queue_name" {
  description = "Service Bus queue name for document events"
  type        = string
  default     = "document-events"
}

variable "transfer_events_queue_name" {
  description = "Service Bus queue name for transfer events"
  type        = string
  default     = "transfer-events"
}

