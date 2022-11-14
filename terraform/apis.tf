locals {
  apis = [
    "aiplatform.googleapis.com",
    "analytics.googleapis.com",
    "analyticsadmin.googleapis.com",
    "analyticsreporting.googleapis.com",
    "logging.googleapis.com",
    "pubsub.googleapis.com",
    "storage-api.googleapis.com",
    "storage-component.googleapis.com",
    "cloudscheduler.googleapis.com",
  ]
}

resource "google_project_service" "aiplatform" {
  for_each = toset(local.apis)

  project = var.project_id
  service = each.key
}
