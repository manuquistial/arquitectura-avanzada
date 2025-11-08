# Azure Key Vault Secret for Service Bus
# This automatically creates the Service Bus credentials secret in Key Vault during deployment

resource "azurerm_key_vault_secret" "servicebus" {
  count = var.key_vault_id != "" ? 1 : 0
  name  = "servicebus"
  value = jsonencode({
    connection-string = azurerm_servicebus_namespace_authorization_rule.main.primary_connection_string
    namespace         = azurerm_servicebus_namespace.main.name
  })
  key_vault_id = var.key_vault_id

  tags = {
    Environment = var.environment
    Component   = "servicebus"
    AutoManaged = "true"
  }

  depends_on = [
    azurerm_servicebus_namespace.main,
    azurerm_servicebus_namespace_authorization_rule.main
  ]
}

# Queue-scoped connection string (Listen) for citizen-events
resource "azurerm_key_vault_secret" "servicebus_citizen_events" {
  count = var.key_vault_id != "" ? 1 : 0
  name  = "servicebus-citizen-events"
  value = jsonencode({
    connection-string = azurerm_servicebus_queue_authorization_rule.citizen_events_listen.primary_connection_string
    queue             = azurerm_servicebus_queue.citizen_events.name
    namespace         = azurerm_servicebus_namespace.main.name
  })
  key_vault_id = var.key_vault_id

  tags = {
    Environment = var.environment
    Component   = "servicebus"
    Queue       = var.citizen_events_queue_name
    AutoManaged = "true"
  }

  depends_on = [
    azurerm_servicebus_queue.citizen_events,
    azurerm_servicebus_queue_authorization_rule.citizen_events_listen
  ]
}

# Queue-scoped connection string (Listen) for document-events
resource "azurerm_key_vault_secret" "servicebus_document_events" {
  count = var.key_vault_id != "" ? 1 : 0
  name  = "servicebus-document-events"
  value = jsonencode({
    connection-string = azurerm_servicebus_queue_authorization_rule.document_events_listen.primary_connection_string
    queue             = azurerm_servicebus_queue.document_events.name
    namespace         = azurerm_servicebus_namespace.main.name
  })
  key_vault_id = var.key_vault_id

  tags = {
    Environment = var.environment
    Component   = "servicebus"
    Queue       = var.document_events_queue_name
    AutoManaged = "true"
  }

  depends_on = [
    azurerm_servicebus_queue.document_events,
    azurerm_servicebus_queue_authorization_rule.document_events_listen
  ]
}

# Queue-scoped connection string (Listen) for transfer-events
resource "azurerm_key_vault_secret" "servicebus_transfer_events" {
  count = var.key_vault_id != "" ? 1 : 0
  name  = "servicebus-transfer-events"
  value = jsonencode({
    connection-string = azurerm_servicebus_queue_authorization_rule.transfer_events_listen.primary_connection_string
    queue             = azurerm_servicebus_queue.transfer_events.name
    namespace         = azurerm_servicebus_namespace.main.name
  })
  key_vault_id = var.key_vault_id

  tags = {
    Environment = var.environment
    Component   = "servicebus"
    Queue       = var.transfer_events_queue_name
    AutoManaged = "true"
  }

  depends_on = [
    azurerm_servicebus_queue.transfer_events,
    azurerm_servicebus_queue_authorization_rule.transfer_events_listen
  ]
}

