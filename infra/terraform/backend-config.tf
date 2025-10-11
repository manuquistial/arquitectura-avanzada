terraform {
  # Backend local - Ideal para proyectos universitarios
  # El estado se guarda localmente en terraform.tfstate
  backend "local" {
    path = "terraform.tfstate"
  }
}
