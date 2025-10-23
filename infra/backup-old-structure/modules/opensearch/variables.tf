variable "namespace" {
  description = "Kubernetes namespace for OpenSearch"
  type        = string
  default     = "default"
}

variable "chart_version" {
  description = "OpenSearch Helm chart version"
  type        = string
  default     = "2.17.0"
}

variable "dashboards_chart_version" {
  description = "OpenSearch Dashboards Helm chart version"
  type        = string
  default     = "2.15.0"
}

variable "storage_size" {
  description = "PVC storage size"
  type        = string
  default     = "8Gi"
}

variable "storage_class" {
  description = "Storage class for PVC (Azure Premium SSD)"
  type        = string
  default     = "managed-premium"
}

variable "memory_request" {
  description = "Memory request for OpenSearch pod"
  type        = string
  default     = "1Gi"
}

variable "memory_limit" {
  description = "Memory limit for OpenSearch pod"
  type        = string
  default     = "2Gi"
}

variable "cpu_request" {
  description = "CPU request for OpenSearch pod"
  type        = string
  default     = "500m"
}

variable "cpu_limit" {
  description = "CPU limit for OpenSearch pod"
  type        = string
  default     = "1000m"
}

variable "heap_size" {
  description = "Java heap size (should be 50% of memory limit)"
  type        = string
  default     = "1g"
}

variable "opensearch_username" {
  description = "OpenSearch admin username"
  type        = string
  default     = "admin"
  sensitive   = true
}

variable "opensearch_password" {
  description = "OpenSearch admin password"
  type        = string
  sensitive   = true
}

variable "enable_dashboards" {
  description = "Enable OpenSearch Dashboards"
  type        = bool
  default     = true
}

