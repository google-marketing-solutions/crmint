locals {
  apis = [
    "aiplatform.googleapis.com",
    "analytics.googleapis.com",
    "analyticsadmin.googleapis.com",
    "analyticsreporting.googleapis.com",
    "cloudbuild.googleapis.com",
    "cloudscheduler.googleapis.com",
    "compute.googleapis.com",
    "logging.googleapis.com",
    "pubsub.googleapis.com",
    "secretmanager.googleapis.com",
    "servicenetworking.googleapis.com",
    "sqladmin.googleapis.com",
    "storage-api.googleapis.com",
    "storage-component.googleapis.com",
  ]
}

resource "google_project_service" "apis" {
  for_each = toset(local.apis)

  project = var.project_id
  service = each.key

  disable_dependent_services = true
}

resource "google_project_service" "vpcaccess" {
  count = var.use_vpc ? 1 : 0
  provider = google-beta

  project = var.network_project_id != null ? var.network_project_id : var.project_id
  service = "vpcaccess.googleapis.com"

  disable_dependent_services = true
}
