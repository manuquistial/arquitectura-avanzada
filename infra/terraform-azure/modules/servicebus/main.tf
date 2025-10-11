resource "azurerm_servicebus_namespace" "main" {
  name                = "${var.environment}-carpeta-bus"
  location            = var.location
  resource_group_name = var.resource_group_name
  sku                 = var.sku
  
  tags = {
    Environment = var.environment
  }
}

# Queue para eventos (equivalente a SQS)
resource "azurerm_servicebus_queue" "events" {
  name         = "events-queue"
  namespace_id = azurerm_servicebus_namespace.main.id
  
  max_size_in_megabytes = 1024
  default_message_ttl   = "P14D"  # 14 días
  
  dead_lettering_on_message_expiration = true
  max_delivery_count                   = 10
}

# Topic para notificaciones (equivalente a SNS)
resource "azurerm_servicebus_topic" "notifications" {
  name         = "notifications-topic"
  namespace_id = azurerm_servicebus_namespace.main.id
  
  max_size_in_megabytes = 1024
  default_message_ttl   = "P14D"
}

# Subscription para el topic
resource "azurerm_servicebus_subscription" "notifications_sub" {
  name               = "all-notifications"
  topic_id           = azurerm_servicebus_topic.notifications.id
  max_delivery_count = 10
  
  dead_lettering_on_message_expiration = true
}

# Authorization rules
resource "azurerm_servicebus_namespace_authorization_rule" "listen_send" {
  name         = "listen-send"
  namespace_id = azurerm_servicebus_namespace.main.id
  
  listen = true
  send   = true
  manage = false
}

