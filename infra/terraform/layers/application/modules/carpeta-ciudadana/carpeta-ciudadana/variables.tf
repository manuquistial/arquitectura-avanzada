# Carpeta Ciudadana Module Variables

# Namespace configuration
variable "namespace" {
  description = "Kubernetes namespace for the application"
  type        = string
  default     = "carpeta-ciudadana-dev"
}

variable "create_namespace" {
  description = "Whether to create the namespace"
  type        = bool
  default     = true
}

# Helm chart configuration
variable "chart_path" {
  description = "Path to the Helm chart"
  type        = string
  default     = "../../../deploy/helm/carpeta-ciudadana"
}

variable "chart_version" {
  description = "Version of the Helm chart"
  type        = string
  default     = "0.1.0"
}

variable "timeout" {
  description = "Timeout for Helm deployment"
  type        = number
  default     = 600
}

# Global configuration
variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "image_registry" {
  description = "Docker image registry"
  type        = string
  default     = "manuelquistial"
}

variable "image_pull_policy" {
  description = "Image pull policy"
  type        = string
  default     = "IfNotPresent"
}

variable "log_level" {
  description = "Log level for services"
  type        = string
  default     = "INFO"
}

# Workload Identity configuration
variable "use_workload_identity" {
  description = "Enable Workload Identity"
  type        = bool
  default     = true
}

variable "workload_identity_client_id" {
  description = "Workload Identity client ID"
  type        = string
  default     = ""
}

variable "workload_identity_tenant_id" {
  description = "Workload Identity tenant ID"
  type        = string
  default     = ""
}

# Feature flags
# keyvault_enabled removed - using traditional Kubernetes secrets

variable "azure_b2c_enabled" {
  description = "Enable Azure B2C authentication"
  type        = bool
  default     = false
}

variable "m2m_auth_enabled" {
  description = "Enable M2M authentication"
  type        = bool
  default     = true
}

variable "migrations_enabled" {
  description = "Enable database migrations"
  type        = bool
  default     = false
}

# Service Bus variables - REMOVED

# Resource optimization
variable "resource_optimization_enabled" {
  description = "Enable resource optimization for limited environments"
  type        = bool
  default     = true
}

variable "max_replicas" {
  description = "Maximum replicas per service"
  type        = number
  default     = 2
}

variable "default_cpu_request" {
  description = "Default CPU request"
  type        = string
  default     = "100m"
}

variable "default_memory_request" {
  description = "Default memory request"
  type        = string
  default     = "128Mi"
}

variable "default_cpu_limit" {
  description = "Default CPU limit"
  type        = string
  default     = "300m"
}

variable "default_memory_limit" {
  description = "Default memory limit"
  type        = string
  default     = "512Mi"
}

# Security configuration
variable "cors_origins" {
  description = "CORS allowed origins"
  type        = string
  default     = "http://localhost:3000,http://localhost:3001"
}

variable "hsts_enabled" {
  description = "Enable HSTS security headers"
  type        = bool
  default     = false
}

variable "csp_enabled" {
  description = "Enable Content Security Policy"
  type        = bool
  default     = true
}

variable "csp_report_uri" {
  description = "CSP violation reporting endpoint"
  type        = string
  default     = ""
}

# Database configuration
variable "database_url" {
  description = "Database connection URL"
  type        = string
  sensitive   = true
}

variable "postgres_uri" {
  description = "PostgreSQL connection URI"
  type        = string
  sensitive   = true
}

variable "m2m_secret_name" {
  description = "M2M authentication secret name"
  type        = string
  default     = "m2m-auth"
}

variable "m2m_secret_key" {
  description = "M2M authentication secret key"
  type        = string
  sensitive   = true
}

# Azure configuration
variable "azure_storage_account_name" {
  description = "Azure Storage account name"
  type        = string
  default     = ""
}

variable "azure_storage_account_key" {
  description = "Azure Storage account key"
  type        = string
  default     = ""
  sensitive   = true
}

variable "azure_storage_container_name" {
  description = "Azure Storage container name"
  type        = string
  default     = "documents"
}

# Azure B2C configuration (if enabled)
variable "azure_b2c_tenant_name" {
  description = "Azure B2C tenant name"
  type        = string
  default     = ""
}

variable "azure_b2c_tenant_id" {
  description = "Azure B2C tenant ID"
  type        = string
  default     = ""
}

variable "azure_b2c_client_id" {
  description = "Azure B2C client ID"
  type        = string
  default     = ""
}

variable "azure_b2c_client_secret" {
  description = "Azure B2C client secret"
  type        = string
  default     = ""
  sensitive   = true
}

# MinTIC configuration
variable "mintic_hub_url" {
  description = "MinTIC Hub URL"
  type        = string
  default     = "https://govcarpeta-apis-4905ff3c005b.herokuapp.com"
}

variable "mintic_operator_id" {
  description = "MinTIC Operator ID"
  type        = string
  default     = "demo-operator"
}

variable "mintic_operator_name" {
  description = "MinTIC Operator Name"
  type        = string
  default     = "Demo Operator"
}

# Service configurations (maps)
variable "frontend_config" {
  description = "Frontend service configuration"
  type = object({
    enabled      = bool
    replicaCount = number
    resources = object({
      requests = object({
        cpu    = string
        memory = string
      })
      limits = object({
        cpu    = string
        memory = string
      })
    })
    autoscaling = object({
      enabled = bool
    })
  })
  default = {
    enabled      = true
    replicaCount = 2
    resources = {
      requests = {
        cpu    = "50m"
        memory = "64Mi"
      }
      limits = {
        cpu    = "200m"
        memory = "256Mi"
      }
    }
    autoscaling = {
      enabled = false
    }
  }
}


variable "citizen_config" {
  description = "Citizen service configuration"
  type = object({
    enabled      = bool
    replicaCount = number
    resources = object({
      requests = object({
        cpu    = string
        memory = string
      })
      limits = object({
        cpu    = string
        memory = string
      })
    })
    autoscaling = object({
      enabled     = bool
      minReplicas = number
      maxReplicas = number
    })
  })
  default = {
    enabled      = true
    replicaCount = 1
    resources = {
      requests = {
        cpu    = "50m"
        memory = "64Mi"
      }
      limits = {
        cpu    = "500m"
        memory = "256Mi"
      }
    }
    autoscaling = {
      enabled     = true
      minReplicas = 2
      maxReplicas = 10
    }
  }
}

variable "ingestion_config" {
  description = "Ingestion service configuration"
  type = object({
    enabled      = bool
    replicaCount = number
    resources = object({
      requests = object({
        cpu    = string
        memory = string
      })
      limits = object({
        cpu    = string
        memory = string
      })
    })
    autoscaling = object({
      enabled     = bool
      minReplicas = number
      maxReplicas = number
    })
  })
  default = {
    enabled      = true
    replicaCount = 1
    resources = {
      requests = {
        cpu    = "50m"
        memory = "64Mi"
      }
      limits = {
        cpu    = "500m"
        memory = "256Mi"
      }
    }
    autoscaling = {
      enabled     = true
      minReplicas = 2
      maxReplicas = 15
    }
  }
}

variable "signature_config" {
  description = "Signature service configuration"
  type = object({
    enabled      = bool
    replicaCount = number
    resources = object({
      requests = object({
        cpu    = string
        memory = string
      })
      limits = object({
        cpu    = string
        memory = string
      })
    })
    autoscaling = object({
      enabled     = bool
      minReplicas = number
      maxReplicas = number
    })
  })
  default = {
    enabled      = true
    replicaCount = 1
    resources = {
      requests = {
        cpu    = "200m"
        memory = "256Mi"
      }
      limits = {
        cpu    = "500m"
        memory = "512Mi"
      }
    }
    autoscaling = {
      enabled     = true
      minReplicas = 2
      maxReplicas = 10
    }
  }
}

variable "metadata_config" {
  description = "Metadata service configuration"
  type = object({
    enabled      = bool
    replicaCount = number
    resources = object({
      requests = object({
        cpu    = string
        memory = string
      })
      limits = object({
        cpu    = string
        memory = string
      })
    })
    autoscaling = object({
      enabled     = bool
      minReplicas = number
      maxReplicas = number
    })
  })
  default = {
    enabled      = true
    replicaCount = 1
    resources = {
      requests = {
        cpu    = "50m"
        memory = "64Mi"
      }
      limits = {
        cpu    = "300m"
        memory = "256Mi"
      }
    }
    autoscaling = {
      enabled     = true
      minReplicas = 2
      maxReplicas = 10
    }
  }
}

variable "transfer_config" {
  description = "Transfer service configuration"
  type = object({
    enabled      = bool
    replicaCount = number
    resources = object({
      requests = object({
        cpu    = string
        memory = string
      })
      limits = object({
        cpu    = string
        memory = string
      })
    })
    autoscaling = object({
      enabled     = bool
      minReplicas = number
      maxReplicas = number
    })
  })
  default = {
    enabled      = true
    replicaCount = 1
    resources = {
      requests = {
        cpu    = "50m"
        memory = "64Mi"
      }
      limits = {
        cpu    = "300m"
        memory = "256Mi"
      }
    }
    autoscaling = {
      enabled     = true
      minReplicas = 2
      maxReplicas = 10
    }
  }
}


variable "read_models_config" {
  description = "Read Models service configuration"
  type = object({
    enabled      = bool
    replicaCount = number
    resources = object({
      requests = object({
        cpu    = string
        memory = string
      })
      limits = object({
        cpu    = string
        memory = string
      })
    })
    autoscaling = object({
      enabled     = bool
      minReplicas = number
      maxReplicas = number
    })
  })
  default = {
    enabled      = true
    replicaCount = 1
    resources = {
      requests = {
        cpu    = "50m"
        memory = "64Mi"
      }
      limits = {
        cpu    = "300m"
        memory = "256Mi"
      }
    }
    autoscaling = {
      enabled     = true
      minReplicas = 2
      maxReplicas = 10
    }
  }
}

variable "mintic_client_config" {
  description = "MinTIC Client service configuration"
  type = object({
    enabled      = bool
    replicaCount = number
    resources = object({
      requests = object({
        cpu    = string
        memory = string
      })
      limits = object({
        cpu    = string
        memory = string
      })
    })
    autoscaling = object({
      enabled     = bool
      minReplicas = number
      maxReplicas = number
    })
  })
  default = {
    enabled      = true
    replicaCount = 1
    resources = {
      requests = {
        cpu    = "100m"
        memory = "128Mi"
      }
      limits = {
        cpu    = "300m"
        memory = "512Mi"
      }
    }
    autoscaling = {
      enabled     = true
      minReplicas = 2
      maxReplicas = 10
    }
  }
}

variable "transfer_worker_config" {
  description = "Transfer Worker service configuration"
  type = object({
    enabled      = bool
    replicaCount = number
    resources = object({
      requests = object({
        cpu    = string
        memory = string
      })
      limits = object({
        cpu    = string
        memory = string
      })
    })
  })
  default = {
    enabled      = true
    replicaCount = 0 # KEDA controls replicas
    resources = {
      requests = {
        cpu    = "50m"
        memory = "64Mi"
      }
      limits = {
        cpu    = "200m"
        memory = "256Mi"
      }
    }
  }
}
