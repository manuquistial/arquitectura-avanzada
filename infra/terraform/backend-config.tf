terraform {
  # Backend remoto en Azure Storage
  # El estado persiste entre ejecuciones del pipeline CI/CD
  backend "azurerm" {
    resource_group_name  = "terraform-state-rg"
    storage_account_name = "tfstatecarpeta"
    container_name       = "tfstate"
    key                  = "carpeta-ciudadana.tfstate"
  }
}
