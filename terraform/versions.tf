terraform {
  required_providers {
    google = {
      source = "hashicorp/google"
      version = "4.43.1"
    }
    google-beta = {
      source = "hashicorp/google-beta"
      version = "4.43.1"
    }
    random = {
      source = "hashicorp/random"
      version = "3.4.3"
    }
    tls = {
      source = "hashicorp/tls"
      version = "4.0.4"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}
