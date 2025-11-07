# Azure Service Bus Namespace
resource "azurerm_servicebus_namespace" "main" {
  name                = "${var.environment}-carpeta-servicebus"
  location            = var.location
  resource_group_name = var.resource_group_name
  sku                 = var.sku
  capacity            = var.capacity

  # Security configuration
  public_network_access_enabled = var.public_network_access_enabled
  minimum_tls_version            = var.minimum_tls_version

  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
    Service     = "Service Bus"
  }
}

# Service Bus Authorization Rule (for connection string)
resource "azurerm_servicebus_namespace_authorization_rule" "main" {
  name         = "RootManageSharedAccessKey"
  namespace_id = azurerm_servicebus_namespace.main.id

  listen = true
  send   = true
  manage = true
}

# Queue for citizen events
resource "azurerm_servicebus_queue" "citizen_events" {
  name                = var.citizen_events_queue_name
  namespace_id        = azurerm_servicebus_namespace.main.id
  max_size_in_megabytes = 1024
}

# Authorization rule with Listen on the queue (principle of least privilege)
resource "azurerm_servicebus_queue_authorization_rule" "citizen_events_listen" {
  name     = "listen-policy"
  queue_id = azurerm_servicebus_queue.citizen_events.id

  listen = true
  send   = false
  manage = false
}

# Queue for document events
resource "azurerm_servicebus_queue" "document_events" {
  name                  = var.document_events_queue_name
  namespace_id          = azurerm_servicebus_namespace.main.id
  max_size_in_megabytes = 1024
}

# Authorization rule with Listen on the document-events queue
resource "azurerm_servicebus_queue_authorization_rule" "document_events_listen" {
  name     = "listen-policy"
  queue_id = azurerm_servicebus_queue.document_events.id

  listen = true
  send   = false
  manage = false
}

# Queue for transfer events
resource "azurerm_servicebus_queue" "transfer_events" {
  name                  = var.transfer_events_queue_name
  namespace_id          = azurerm_servicebus_namespace.main.id
  max_size_in_megabytes = 1024
}

# Authorization rule with Listen on the transfer-events queue
resource "azurerm_servicebus_queue_authorization_rule" "transfer_events_listen" {
  name     = "listen-policy"
  queue_id = azurerm_servicebus_queue.transfer_events.id

  listen = true
  send   = false
  manage = false
}

