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

    maintenance_window {
      day  = 7
      hour = 2
    }
  }
}

resource "google_sql_database" "crmint" {
  name     = var.database_name
  instance = google_sql_database_instance.main.name
}

resource "random_password" "main_db_password" {
  length = 16
}

resource "google_sql_user" "crmint" {
  name     = var.database_user
  instance = google_sql_database_instance.main.name
  password = random_password.main_db_password.result
}
