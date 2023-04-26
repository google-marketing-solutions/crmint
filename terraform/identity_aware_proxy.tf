resource "google_project_service" "iap_service" {
  project = var.project_id
  service = "iap.googleapis.com"
}

resource "google_iap_brand" "default" {
  count = var.iap_brand_id == null ? 1 : 0
  support_email     = var.iap_support_email
  application_title = "Cloud IAP protected Application"
  project           = google_project_service.iap_service.project
}

resource "google_iap_client" "default" {
  display_name = "Test Client"
  brand        =  var.iap_brand_id == null ? google_iap_brand.default[0].name : "projects/${var.project_id}/brands/${var.iap_brand_id}"
}

resource "google_project_service_identity" "iap_sa" {
  provider = google-beta
  project  = google_project_service.iap_service.project
  service  = "iap.googleapis.com"
}
