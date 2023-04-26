resource "google_service_account" "frontend_sa" {
  account_id   = "crmint-frontend-sa"
  display_name = "CRMint Frontend Service Account"
  project      = var.project_id
}

resource "google_service_account" "jobs_sa" {
  account_id   = "crmint-jobs-sa"
  display_name = "CRMint Jobs Service Account"
  project      = var.project_id
}

resource "google_service_account" "controller_sa" {
  account_id   = "crmint-controller-sa"
  display_name = "CRMint Controller Service Account"
  project      = var.project_id
}

resource "google_service_account" "pubsub_sa" {
  account_id   = "crmint-pubsub-sa"
  display_name = "CRMint PubSub Service Account"
  project      = var.project_id
}

resource "google_project_service_identity" "cloudbuild_managed_sa" {
  provider = google-beta
  project  = var.project_id
  service  = "cloudbuild.googleapis.com"
}

resource "google_project_service_identity" "pubsub_managed_sa" {
  provider = google-beta
  project  = var.project_id
  service  = "pubsub.googleapis.com"
}

resource "google_project_service_identity" "iap_managed_sa" {
  provider = google-beta
  project  = var.project_id
  service  = "iap.googleapis.com"
}

resource "google_project_iam_member" "controller_sa--cloudsql-client" {
  member  = "serviceAccount:${google_service_account.controller_sa.email}"
  project = var.project_id
  role    = "roles/cloudsql.client"
}

resource "google_project_iam_member" "controller_sa--pubsub-publisher" {
  member  = "serviceAccount:${google_service_account.controller_sa.email}"
  project = var.project_id
  role    = "roles/pubsub.publisher"
}

resource "google_project_iam_member" "controller_sa--logging-writer" {
  member  = "serviceAccount:${google_service_account.controller_sa.email}"
  project = var.project_id
  role    = "roles/logging.logWriter"
}

resource "google_project_iam_member" "controller_sa--logging-viewer" {
  member  = "serviceAccount:${google_service_account.controller_sa.email}"
  project = var.project_id
  role    = "roles/logging.viewer"
}

resource "google_project_iam_member" "jobs_sa--pubsub-publisher" {
  member  = "serviceAccount:${google_service_account.jobs_sa.email}"
  project = var.project_id
  role    = "roles/pubsub.publisher"
}

resource "google_project_iam_member" "jobs_sa--logging-writer" {
  member  = "serviceAccount:${google_service_account.jobs_sa.email}"
  project = var.project_id
  role    = "roles/logging.logWriter"
}

resource "google_project_iam_member" "jobs_sa--bigquery-data-editor" {
  member  = "serviceAccount:${google_service_account.jobs_sa.email}"
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
}

resource "google_project_iam_member" "jobs_sa--bigquery-job-user" {
  member  = "serviceAccount:${google_service_account.jobs_sa.email}"
  project = var.project_id
  role    = "roles/bigquery.jobUser"
}

resource "google_project_iam_member" "jobs_sa--bigquery-resource-viewer" {
  member  = "serviceAccount:${google_service_account.jobs_sa.email}"
  project = var.project_id
  role    = "roles/bigquery.resourceViewer"
}

resource "google_project_iam_member" "jobs_sa--storage-object-admin" {
  member  = "serviceAccount:${google_service_account.jobs_sa.email}"
  project = var.project_id
  role    = "roles/storage.objectAdmin"
}

resource "google_project_iam_member" "jobs_sa--aiplatform-user" {
  member  = "serviceAccount:${google_service_account.jobs_sa.email}"
  project = var.project_id
  role    = "roles/aiplatform.user"
}

# Needed to access the controller image during migrations from Cloud Build.
resource "google_project_iam_member" "cloudbuild_managed_sa--object-viewer" {
  member  = "serviceAccount:${google_project_service_identity.cloudbuild_managed_sa.email}"
  project = var.project_id
  role    = "roles/storage.objectViewer"
}

# Needed to access the database during migrations from Cloud Build.
resource "google_project_iam_member" "cloudbuild_managed_sa--cloudsql-client" {
  member  = "serviceAccount:${google_project_service_identity.cloudbuild_managed_sa.email}"
  project = var.project_id
  role    = "roles/cloudsql.client"
}

# Needed for projects created on or before April 8, 2021.
# Grant the Google-managed service account the `iam.serviceAccountTokenCreator` role.
resource "google_project_iam_member" "pubsub_token-creator" {
  member  = "serviceAccount:${google_project_service_identity.pubsub_managed_sa.email}"
  project = var.project_id
  role    = "roles/iam.serviceAccountTokenCreator"
}

##
# Cloud Run permissions
#
# NOTE: We delegate the authentication flow to IAP, so we need to give IAP SA
#       access to Cloud Run.
#

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

data "google_iam_policy" "run_users" {
  binding {
    role = "roles/run.invoker"
    members = [
        "serviceAccount:${google_project_service_identity.iap_sa.email}",
        "serviceAccount:${google_service_account.pubsub_sa.email}",
    ]
  }
}

resource "google_cloud_run_service_iam_policy" "frontend_run-invoker" {
  location = google_cloud_run_service.frontend_run.location
  project = google_cloud_run_service.frontend_run.project
  service = google_cloud_run_service.frontend_run.name
  policy_data = data.google_iam_policy.run_users.policy_data
}

resource "google_cloud_run_service_iam_policy" "controller_run-invoker" {
  location = google_cloud_run_service.controller_run.location
  project = google_cloud_run_service.controller_run.project
  service = google_cloud_run_service.controller_run.name
  policy_data = data.google_iam_policy.run_users.policy_data
}

resource "google_cloud_run_service_iam_policy" "jobs_run-invoker" {
  location = google_cloud_run_service.jobs_run.location
  project = google_cloud_run_service.jobs_run.project
  service = google_cloud_run_service.jobs_run.name
  policy_data = data.google_iam_policy.run_users.policy_data
}
