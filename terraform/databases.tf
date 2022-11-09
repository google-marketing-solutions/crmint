resource "google_sql_database_instance" "main" {
  name             = "crmintapp-db-clone"
  database_version = "MYSQL_8_0"
  region           = var.region

  settings {
    tier = "db-g1-small"

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
  name     = "crmintapp-db"
  instance = google_sql_database_instance.main.name
}

resource "random_password" "main_db_password" {
  length = 16
}

resource "google_sql_user" "crmint" {
  name     = "crmintapp"
  instance = google_sql_database_instance.main.name
  password = random_password.main_db_password.result
}
