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

resource "google_project_iam_member" "controller_sa--cloudsql-client" {
  member  = "serviceAccount:${google_service_account.controller_sa.email}"
  project = var.project_id
  role    = "roles/cloudsql.client"
}
