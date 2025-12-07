locals {
  private_network_self_link = var.use_vpc ? (
    var.use_shared_vpc ? one(data.google_compute_network.shared[*].self_link) : one(google_compute_network.private[*].self_link)
  ) : null
}

resource "null_resource" "debug_values" {
  triggers = {
    always_run = "${timestamp()}"
  }

  provisioner "local-exec" {
    command = <<EOT
      echo "DEBUG_VALUES: use_vpc=${var.use_vpc}"
      echo "DEBUG_VALUES: use_shared_vpc=${var.use_shared_vpc}"
      echo "DEBUG_VALUES: shared_vpc_network=${var.shared_vpc_network}"
      echo "DEBUG_VALUES: shared_vpc_host_project_id=${var.shared_vpc_host_project_id}"
      echo "DEBUG_VALUES: vpc_access_connector_id=${coalesce(var.vpc_access_connector_id, "null")}"
      echo "DEBUG_VALUES: computed_network_link=${var.use_vpc ? (var.use_shared_vpc ? "projects/${var.shared_vpc_host_project_id}/global/networks/${var.shared_vpc_network}" : "LOCAL_PRIVATE") : "DISABLED"}"
    EOT
  }
}

resource "google_sql_database_instance" "main" {

  name             = var.database_instance_name
  database_version = "MYSQL_8_0"
  project          = var.database_project_id != null ? var.database_project_id : var.project_id
  region           = var.database_region != null ? var.database_region : var.region

  settings {
    tier              = var.database_tier
    availability_type = var.database_availability_type

    insights_config {
      query_insights_enabled  = true
      query_string_length     = 1024
      record_application_tags = false
      record_client_address   = false
    }

    dynamic "ip_configuration" {
      # Includes this block only if `var.use_vpc` is true.
      for_each = var.use_vpc ? [1] : []
      content {
        ipv4_enabled = false
        private_network = var.use_shared_vpc ? "projects/${var.shared_vpc_host_project_id}/global/networks/${var.shared_vpc_network}" : google_compute_network.private[0].self_link
      }
    }

    maintenance_window {
      day  = 7
      hour = 2
    }
  }

  depends_on = [
    google_service_networking_connection.private_vpc_connection,
    google_compute_network.private
  ]
}

resource "google_sql_database" "crmint" {
  name     = var.database_name
  instance = google_sql_database_instance.main.name
}

resource "random_password" "main_db_password" {
  length  = 16
  special = false
}

resource "google_sql_user" "crmint" {
  name     = var.database_user
  instance = google_sql_database_instance.main.name
  password = random_password.main_db_password.result
}

output "debug_network_link" {
  value = var.use_vpc ? (
    var.use_shared_vpc ? "projects/${var.shared_vpc_host_project_id}/global/networks/${var.shared_vpc_network}" : (length(google_compute_network.private) > 0 ? google_compute_network.private[0].self_link : "MISSING")
  ) : "VPC_DISABLED"
}
