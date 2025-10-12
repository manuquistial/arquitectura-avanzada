output "namespace_id" {
  description = "Service Bus namespace ID"
  value       = azurerm_servicebus_namespace.carpeta.id
}

output "namespace_name" {
  description = "Service Bus namespace name"
  value       = azurerm_servicebus_namespace.carpeta.name
}

output "primary_connection_string" {
  description = "Primary connection string for services"
  value       = azurerm_servicebus_namespace_authorization_rule.carpeta_services.primary_connection_string
  sensitive   = true
}

output "queue_names" {
  description = "Created queue names"
  value = {
    citizen_registered      = azurerm_servicebus_queue.citizen_registered.name
    document_uploaded       = azurerm_servicebus_queue.document_uploaded.name
    document_authenticated  = azurerm_servicebus_queue.document_authenticated.name
    transfer_requested      = azurerm_servicebus_queue.transfer_requested.name
    transfer_confirmed      = azurerm_servicebus_queue.transfer_confirmed.name
  }
}
