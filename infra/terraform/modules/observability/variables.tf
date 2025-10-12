variable "namespace" {
  description = "Kubernetes namespace for observability stack"
  type        = string
  default     = "observability"
}

variable "otel_chart_version" {
  description = "OpenTelemetry Collector Helm chart version"
  type        = string
  default     = "0.78.0"
}

variable "otel_replicas" {
  description = "Number of OpenTelemetry Collector replicas"
  type        = number
  default     = 2
}

variable "otel_cpu_request" {
  description = "OpenTelemetry Collector CPU request"
  type        = string
  default     = "200m"
}

variable "otel_cpu_limit" {
  description = "OpenTelemetry Collector CPU limit"
  type        = string
  default     = "500m"
}

variable "otel_memory_request" {
  description = "OpenTelemetry Collector memory request"
  type        = string
  default     = "256Mi"
}

variable "otel_memory_limit" {
  description = "OpenTelemetry Collector memory limit"
  type        = string
  default     = "512Mi"
}

variable "prometheus_chart_version" {
  description = "Prometheus Helm chart version"
  type        = string
  default     = "25.8.0"
}

variable "prometheus_retention" {
  description = "Prometheus data retention period"
  type        = string
  default     = "15d"
}

variable "prometheus_storage_size" {
  description = "Prometheus persistent volume size"
  type        = string
  default     = "10Gi"
}

variable "prometheus_cpu_request" {
  description = "Prometheus CPU request"
  type        = string
  default     = "500m"
}

variable "prometheus_cpu_limit" {
  description = "Prometheus CPU limit"
  type        = string
  default     = "1000m"
}

variable "prometheus_memory_request" {
  description = "Prometheus memory request"
  type        = string
  default     = "1Gi"
}

variable "prometheus_memory_limit" {
  description = "Prometheus memory limit"
  type        = string
  default     = "2Gi"
}

