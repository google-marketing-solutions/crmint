resource "google_project_service" "iap_service" {
  project = var.project_id
  service = "iap.googleapis.com"
}

resource "google_iap_brand" "default" {
  support_email     = var.iap_support_email
  application_title = "Cloud IAP protected Application"
  project           = google_project_service.iap_service.project
}

resource "google_project_service_identity" "iap_sa" {
  provider = google-beta
  project  = google_project_service.iap_service.project
  service  = "iap.googleapis.com"
}

resource "google_project_iam_member" "iap_sa--run_invoker" {
  project = google_project_service.iap_service.project
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_project_service_identity.iap_sa.email}"
}

resource "google_iap_client" "default" {
  display_name = "Test Client"
  brand        =  google_iap_brand.default.name
}

data "google_iam_policy" "iap_users" {
  binding {
    role = "roles/iap.httpsResourceAccessor"
    members = concat(
      ["serviceAccount:${google_service_account.pubsub_sa.email}"],
      var.iap_allowed_users
    )
  }
}

resource "google_iap_web_backend_service_iam_policy" "frontend" {
  project = google_compute_backend_service.frontend_backend.project
  web_backend_service = google_compute_backend_service.frontend_backend.name
  policy_data = data.google_iam_policy.iap_users.policy_data
}

resource "google_iap_web_backend_service_iam_policy" "controller" {
  project = google_compute_backend_service.controller_backend.project
  web_backend_service = google_compute_backend_service.controller_backend.name
  policy_data = data.google_iam_policy.iap_users.policy_data
}

resource "google_iap_web_backend_service_iam_policy" "jobs" {
  project = google_compute_backend_service.jobs_backend.project
  web_backend_service = google_compute_backend_service.jobs_backend.name
  policy_data = data.google_iam_policy.iap_users.policy_data
}
