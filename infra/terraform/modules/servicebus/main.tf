/**
 * Azure Service Bus Module
 * Creates Service Bus namespace (Basic tier) and queues for event-driven architecture
 */

resource "azurerm_servicebus_namespace" "carpeta" {
  name                = var.namespace_name
  location            = var.location
  resource_group_name = var.resource_group_name
  sku                 = "Basic"  # ~$0.05/month, 1M operations included
  
  tags = var.tags
}

# Queue: citizen-registered
resource "azurerm_servicebus_queue" "citizen_registered" {
  name         = "citizen-registered"
  namespace_id = azurerm_servicebus_namespace.carpeta.id
  
  max_size_in_megabytes      = 1024  # 1 GB (Basic tier)
  default_message_ttl        = "P14D"  # 14 days
  
  # Dead Letter Queue (DLQ) configuration
  dead_lettering_on_message_expiration = true
  batched_operations_enabled = true
  
  # Retry configuration
  max_delivery_count         = 5  # Send to DLQ after 5 delivery attempts
  lock_duration              = "PT5M"  # 5 minutes lock duration
  
  # Deduplication
  requires_duplicate_detection = true
  duplicate_detection_history_time_window = "PT10M"  # 10 minutes
}

# Queue: document-uploaded
resource "azurerm_servicebus_queue" "document_uploaded" {
  name         = "document-uploaded"
  namespace_id = azurerm_servicebus_namespace.carpeta.id
  
  max_size_in_megabytes      = 1024
  default_message_ttl        = "P14D"
  
  dead_lettering_on_message_expiration = true
  batched_operations_enabled = true
  max_delivery_count         = 5
  lock_duration              = "PT5M"
  
  requires_duplicate_detection = true
  duplicate_detection_history_time_window = "PT10M"
}

# Queue: document-authenticated
resource "azurerm_servicebus_queue" "document_authenticated" {
  name         = "document-authenticated"
  namespace_id = azurerm_servicebus_namespace.carpeta.id
  
  max_size_in_megabytes      = 1024
  default_message_ttl        = "P14D"
  
  dead_lettering_on_message_expiration = true
  batched_operations_enabled = true
  max_delivery_count         = 5
  lock_duration              = "PT5M"
  
  requires_duplicate_detection = true
  duplicate_detection_history_time_window = "PT10M"
}

# Queue: transfer-requested
resource "azurerm_servicebus_queue" "transfer_requested" {
  name         = "transfer-requested"
  namespace_id = azurerm_servicebus_namespace.carpeta.id
  
  max_size_in_megabytes      = 1024
  default_message_ttl        = "P14D"
  
  dead_lettering_on_message_expiration = true
  batched_operations_enabled = true
  max_delivery_count         = 5
  lock_duration              = "PT5M"
  
  requires_duplicate_detection = true
  duplicate_detection_history_time_window = "PT10M"
}

# Queue: transfer-confirmed
resource "azurerm_servicebus_queue" "transfer_confirmed" {
  name         = "transfer-confirmed"
  namespace_id = azurerm_servicebus_namespace.carpeta.id
  
  max_size_in_megabytes      = 1024
  default_message_ttl        = "P14D"
  
  dead_lettering_on_message_expiration = true
  batched_operations_enabled = true
  max_delivery_count         = 5
  lock_duration              = "PT5M"
  
  requires_duplicate_detection = true
  duplicate_detection_history_time_window = "PT10M"
}

# Authorization Rule for services (Send + Listen)
resource "azurerm_servicebus_namespace_authorization_rule" "carpeta_services" {
  name         = "carpeta-services-policy"
  namespace_id = azurerm_servicebus_namespace.carpeta.id
  
  listen = true
  send   = true
  manage = false
}
