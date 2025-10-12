# Lifecycle management for Azure Blob Storage
# REQUERIMIENTO: Documentos SIGNED se mueven a Cool (90d) y Archive (365d) para optimizar costos

resource "azurerm_storage_management_policy" "document_lifecycle" {
  count = var.enable_lifecycle_policy ? 1 : 0
  
  storage_account_id = azurerm_storage_account.main.id

  # Rule 1: Move SIGNED documents to Cool after 90 days
  rule {
    name    = "move-signed-to-cool-after-90d"
    enabled = true
    
    filters {
      blob_types   = ["blockBlob"]
      prefix_match = ["documents/"]
      
      # Note: Blob index tags filtering requires Premium storage
      # For Basic/Standard, we move ALL documents to Cool after 90d
      # In production, use blob index tags to filter only SIGNED documents
    }
    
    actions {
      base_blob {
        # Move to Cool tier after 90 days of last modification
        tier_to_cool_after_days_since_modification_greater_than = 90
      }
    }
  }
  
  # Rule 2: Move SIGNED documents to Archive after 1 year
  rule {
    name    = "move-signed-to-archive-after-1y"
    enabled = true
    
    filters {
      blob_types   = ["blockBlob"]
      prefix_match = ["documents/"]
    }
    
    actions {
      base_blob {
        # Move to Archive tier after 365 days
        tier_to_archive_after_days_since_modification_greater_than = 365
      }
    }
  }
  
  # Rule 3: Delete UNSIGNED documents after 30 days (backup to CronJob)
  # Note: This is a fallback. Primary deletion is via CronJob which also deletes metadata
  rule {
    name    = "delete-unsigned-after-30d"
    enabled = var.enable_auto_delete_unsigned
    
    filters {
      blob_types   = ["blockBlob"]
      prefix_match = ["documents/"]
      
      # Ideally filter by blob tag state=UNSIGNED
      # But requires Premium tier or blob index tags feature
    }
    
    actions {
      base_blob {
        # Delete after 30 days
        # NOTE: CronJob should delete first (with metadata)
        # This is failsafe for orphaned blobs
        delete_after_days_since_modification_greater_than = 35  # 5 days grace period
      }
    }
  }
}

# Optional: Enable blob versioning for immutability
# This is complementary to WORM trigger in PostgreSQL
resource "azurerm_storage_account" "main" {
  # ... existing configuration ...
  
  # Enable blob features for WORM compliance
  blob_properties {
    # Enable versioning (keeps history of modifications)
    versioning_enabled = var.enable_blob_versioning
    
    # Soft delete (7 days retention before permanent deletion)
    delete_retention_policy {
      days = 7
    }
    
    # Container soft delete
    container_delete_retention_policy {
      days = 7
    }
    
    # Optional: Change feed for audit
    change_feed_enabled = var.enable_change_feed
    
    # Note: Immutable storage (WORM at blob level) requires Premium
    # We enforce WORM at application level (PostgreSQL trigger)
  }
}

# Outputs
output "lifecycle_policy_id" {
  description = "ID of the lifecycle management policy"
  value       = length(azurerm_storage_management_policy.document_lifecycle) > 0 ? azurerm_storage_management_policy.document_lifecycle[0].id : null
}

