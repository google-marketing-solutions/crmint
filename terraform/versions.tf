terraform {
  required_providers {
    google = {
      source = "hashicorp/google"
      version = "5.0.0"
    }
    google-beta = {
      source = "hashicorp/google-beta"
      version = "5.0.0"
    }
    random = {
      source = "hashicorp/random"
      version = "3.4.3"
    }
  }
}

provider "google" {
  access_token = var.test_google_access_token
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  access_token = var.test_google_access_token
  project = var.project_id
  region  = var.region
}
