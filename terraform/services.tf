resource "google_cloud_run_service" "frontend_run" {
  name     = "frontend"
  location = var.region
  project  = var.project_id

  metadata {
    annotations = {
      # For valid annotation values and descriptions, see
      # https://cloud.google.com/sdk/gcloud/reference/run/deploy#--ingress
      "run.googleapis.com/ingress" = "internal-and-cloud-load-balancing"
    }
  }

  template {
    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale" = "1"
        "autoscaling.knative.dev/maxScale" = "1"
      }
    }

    spec {
      service_account_name = google_service_account.frontend_sa.email

      containers {
        image = "europe-docker.pkg.dev/${var.project_id}/crmint/frontend:latest"
      }
    }
  }

  autogenerate_revision_name = true

  traffic {
    percent         = 100
    latest_revision = true
  }
}

resource "google_cloud_run_service_iam_member" "frontend_run-public" {
  location = google_cloud_run_service.frontend_run.location
  project = google_cloud_run_service.frontend_run.project
  service = google_cloud_run_service.frontend_run.name
  role = "roles/run.invoker"
  member = "allUsers"
}

resource "google_cloud_run_service" "controller_run" {
  provider = google-beta
  name     = "controller"
  location = var.region
  project = var.project_id

  metadata {
    annotations = {
      # For valid annotation values and descriptions, see
      # https://cloud.google.com/sdk/gcloud/reference/run/deploy#--ingress
      "run.googleapis.com/ingress" = "internal-and-cloud-load-balancing"
    }
  }

  template {
    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale" = "0"
        "autoscaling.knative.dev/maxScale" = "2"
        "run.googleapis.com/cloudsql-instances" = google_sql_database_instance.main.connection_name
      }
    }

    spec {
      service_account_name = google_service_account.controller_sa.email

      containers {
        image = "europe-docker.pkg.dev/${var.project_id}/crmint/controller:latest"

        # TODO(dulacp): soon available in beta
        # liveness_probe {
        #   initial_delay_seconds = 20
        #   timeout_seconds = 4
        #   period_seconds = 5
        #   failure_threshold = 2

        #   http_get {
        #     path = "/readiness_check"
        #   }
        # }

        env {
          name  = "DATABASE_URI"
          value = "mysql+mysqlconnector://${google_sql_user.crmint.name}:${google_sql_user.crmint.password}@/${google_sql_database.crmint.name}?unix_socket=/cloudsql/${google_sql_database_instance.main.connection_name}"
        }
        env {
          name  = "PUBSUB_VERIFICATION_TOKEN"
          value = random_id.pubsub_verification_token.b64_url
        }
      }
    }
  }

  autogenerate_revision_name = true

  traffic {
    percent         = 100
    latest_revision = true
  }
}

resource "google_cloud_run_service_iam_member" "controller_run-public" {
  location = google_cloud_run_service.controller_run.location
  project = google_cloud_run_service.controller_run.project
  service = google_cloud_run_service.controller_run.name
  role = "roles/run.invoker"
  member = "allUsers"
}

resource "google_cloud_run_service" "jobs_run" {
  provider = google-beta
  name     = "jobs"
  location = var.region
  project = var.project_id

  metadata {
    annotations = {
      # For valid annotation values and descriptions, see
      # https://cloud.google.com/sdk/gcloud/reference/run/deploy#--ingress
      "run.googleapis.com/ingress" = "internal-and-cloud-load-balancing"
    }
  }

  template {
    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale" = "0"
        "autoscaling.knative.dev/maxScale" = "20"
      }
    }
    spec {
      service_account_name = google_service_account.jobs_sa.email

      containers {
        image = "europe-docker.pkg.dev/${var.project_id}/crmint/jobs:latest"

        # TODO(dulacp): soon available in beta
        # liveness_probe {
        #   initial_delay_seconds = 20
        #   timeout_seconds = 4
        #   period_seconds = 5
        #   failure_threshold = 2

        #   http_get {
        #     path = "/readiness_check"
        #   }
        # }

        env {
          name  = "PUBSUB_VERIFICATION_TOKEN"
          value = random_id.pubsub_verification_token.b64_url
        }
      }
    }
  }

  autogenerate_revision_name = true

  traffic {
    percent         = 100
    latest_revision = true
  }
}

resource "google_cloud_run_service_iam_member" "jobs_run-public" {
  location = google_cloud_run_service.jobs_run.location
  project = google_cloud_run_service.jobs_run.project
  service = google_cloud_run_service.jobs_run.name
  role = "roles/run.invoker"
  member = "allUsers"
}
