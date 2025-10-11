output "namespace_id" {
  description = "Service Bus namespace ID"
  value       = azurerm_servicebus_namespace.main.id
}

output "connection_string" {
  description = "Connection string"
  value       = azurerm_servicebus_namespace_authorization_rule.listen_send.primary_connection_string
  sensitive   = true
}

output "queue_name" {
  description = "Queue name"
  value       = azurerm_servicebus_queue.events.name
}

output "topic_name" {
  description = "Topic name"
  value       = azurerm_servicebus_topic.notifications.name
}

