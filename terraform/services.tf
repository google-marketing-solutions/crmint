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
        image = var.frontend_image

        env {
          name  = "APP_TITLE"
          value = var.app_title
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

resource "google_cloud_run_service_iam_member" "frontend_run-public" {
  location = google_cloud_run_service.frontend_run.location
  project = google_cloud_run_service.frontend_run.project
  service = google_cloud_run_service.frontend_run.name
  role = "roles/run.invoker"
  member = "allUsers"
}

locals {
  cloud_db_uri = var.use_vpc ? "mysql+mysqlconnector://${google_sql_user.crmint.name}:${google_sql_user.crmint.password}@${google_sql_database_instance.main.first_ip_address}/${google_sql_database.crmint.name}" : "mysql+mysqlconnector://${google_sql_user.crmint.name}:${google_sql_user.crmint.password}@/${google_sql_database.crmint.name}?unix_socket=/cloudsql/${google_sql_database_instance.main.connection_name}"
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
      annotations = merge(
        {
          "autoscaling.knative.dev/minScale" = "0"
          "autoscaling.knative.dev/maxScale" = "2"
        },
        var.use_vpc ? {
          # Uses the VPC Connector
          "run.googleapis.com/vpc-access-connector" = google_vpc_access_connector.connector[0].name
          # Routes only egress to private ip addresses through the VPC Connector.
          "run.googleapis.com/vpc-access-egress" = "private-ranges-only"
        } : {
          "run.googleapis.com/cloudsql-instances" = google_sql_database_instance.main.connection_name
        }
      )
    }

    spec {
      service_account_name = google_service_account.controller_sa.email

      containers {
        image = var.controller_image

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
          value = local.cloud_db_uri
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
        image = var.jobs_image

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

resource "google_cloudbuild_worker_pool" "private" {
  name = "crmint-private-pool"
  location = var.region

  worker_config {
    disk_size_gb = 100
    machine_type = "e2-standard-2"
    no_external_ip = var.use_vpc ? true : false
  }

  dynamic "network_config" {
    # Includes this block only if `local.private_network` is set to a non-null value.
    for_each = local.private_network[*]
    content {
      peered_network = google_compute_network.private[0].id
    }
  }

  depends_on = [
    google_project_service.aiplatform,
    google_project_service.vpcaccess,
    google_service_networking_connection.private_vpc_connection
  ]
}

# Local variables are used to simplify the definition of outputs.
locals {
  migrate_image = var.controller_image
  migrate_sql_conn_name = google_sql_database_instance.main.connection_name
  pool = google_cloudbuild_worker_pool.private.id
}
