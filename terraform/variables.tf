##
# Google Cloud Project

variable "project_id" {
  description = "GCP Project ID"
}

variable "region" {
  description = "GCP Region"
  default = "us-east1"
}

variable "zone" {
  description = "GCP Zone"
  default = "us-east1-c"
}


##
# Database

variable "database_project_id" {
  description = "Database GCP project to use. Defaults to `var.project_id`."
  default = null
}

variable "database_region" {
  description = "Database region to setup a Cloud SQL instance. Defaults to `var.region`"
  default = null
}

variable "database_tier" {
  description = "Database instance machine tier. Defaults to a small instance."
  default = "db-g1-small"
}

variable "database_availability_type" {
  description = "Database availability type. Defaults to one zone."
  default = "ZONAL"
}

variable "database_instance_name" {
  description = "Name for the Cloud SQL instance."
  default = "crmintapp-db"
}

variable "database_name" {
  description = "Name of the database in your Cloud SQL instance."
  default = "crmintapp-db"
}

variable "database_user" {
  description = "Database user name."
  default = "crmintapp"
}


##
# Services Docker images

variable "controller_image" {
  description = <<EOF
    Docker image uri for the controller service
    (fully qualified uri, meaning with tag)"
  EOF
  default = "europe-docker.pkg.dev/crmint-builds/crmint/controller:latest"
}


##
# Custom domain

variable "custom_domain" {
  description = <<EOF
    (Optional) Custom Domain for the UI (e.g. crmint.example.com).
    Leave this value empty to skip.
    EOF
  default = ""
}


##
# IAP configuration

variable "iap_support_email" {
  description = "Support email used for configuring IAP"
}

variable "iap_allowed_users" {
  type = list
}
