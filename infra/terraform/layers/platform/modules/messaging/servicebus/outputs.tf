output "servicebus_namespace_id" {
  description = "Azure Service Bus Namespace ID"
  value       = azurerm_servicebus_namespace.main.id
}

output "servicebus_namespace_name" {
  description = "Azure Service Bus Namespace name"
  value       = azurerm_servicebus_namespace.main.name
}

output "servicebus_connection_string" {
  description = "Azure Service Bus connection string"
  value       = azurerm_servicebus_namespace_authorization_rule.main.primary_connection_string
  sensitive   = true
}

output "servicebus_primary_key" {
  description = "Azure Service Bus primary key"
  value       = azurerm_servicebus_namespace_authorization_rule.main.primary_key
  sensitive   = true
}

