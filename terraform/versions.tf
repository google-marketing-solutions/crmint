terraform {
  required_providers {
    google = {
      source = "hashicorp/google"
      version = "4.42.1"
    }
    random = {
      source = "hashicorp/random"
      version = "3.4.3"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}
