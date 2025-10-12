/**
 * KEDA Module Variables
 */

variable "keda_version" {
  description = "KEDA Helm chart version"
  type        = string
  default     = "2.13.0"
}

variable "keda_namespace" {
  description = "Kubernetes namespace for KEDA"
  type        = string
  default     = "keda-system"
}

variable "app_namespace" {
  description = "Application namespace for TriggerAuthentication"
  type        = string
  default     = "carpeta-ciudadana-dev"
}

variable "replica_count" {
  description = "Number of replicas for KEDA operator (HA)"
  type        = number
  default     = 2
}

variable "operator_cpu_request" {
  description = "CPU request for KEDA operator"
  type        = string
  default     = "100m"
}

variable "operator_memory_request" {
  description = "Memory request for KEDA operator"
  type        = string
  default     = "128Mi"
}

variable "operator_cpu_limit" {
  description = "CPU limit for KEDA operator"
  type        = string
  default     = "1000m"
}

variable "operator_memory_limit" {
  description = "Memory limit for KEDA operator"
  type        = string
  default     = "1Gi"
}

variable "log_level" {
  description = "Log level for KEDA (debug, info, error)"
  type        = string
  default     = "info"
}

variable "enable_servicebus_trigger" {
  description = "Enable TriggerAuthentication for Azure Service Bus"
  type        = bool
  default     = true
}

variable "enable_prometheus_monitoring" {
  description = "Enable Prometheus monitoring with ServiceMonitor"
  type        = bool
  default     = true
}

