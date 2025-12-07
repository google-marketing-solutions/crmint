##
# Report usage analytics consent

variable "report_usage_id" {
  description = "Report anonymous usage to our analytics to improve the tool."
  nullable    = false
}

##
# Application config

variable "app_title" {
  description = "Project name to display in the UI."
}

variable "notification_sender_email" {
  description = "Email address to send notifications to."
}


##
# Security (IAP configuration)

variable "iap_brand_id" {
  description = "Existing IAP Brand ID - only INTERNAL TYPE (you can obtain it using this command: `$ gcloud iap oauth-brands list --format='value(name)' | sed 's:.*/::'`)."
  default = null
}

variable "iap_support_email" {
  description = "Support email used for configuring IAP"
}

variable "iap_allowed_users" {
  type = list
}


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
# Virtual Private Cloud

variable "use_vpc" {
  description = "Configures the database with a private IP. Default to true."
  default = true
}

variable "network_project_id" {
  description = "Network GCP project to use. Defaults to `var.project_id`."
  default = null
}

variable "network_region" {
  description = "Network region. Defaults to `var.region`."
  default = null
}




variable "use_shared_vpc" {
  description = "Whether to use a Shared VPC from a host project instead of creating a local VPC."
  type        = bool
  default     = true
}

variable "shared_vpc_host_project_id" {
  description = "The ID of the Shared VPC host project."
  type        = string
  default     = "crmint-shared-vpc1"
}

variable "shared_vpc_network" {
  description = "The name of the Shared VPC network."
  type        = string
  default     = "shared-vpc"
}


variable "shared_vpc_subnetwork" {
  description = "The name of the Shared VPC subnetwork to use for the VPC Access Connector. Must have a /28 IP CIDR range if creating a new connector."
  type        = string
  default     = "iowa-2"
}

variable "vpc_access_connector_id" {
  description = "The full ID of an existing VPC Access Connector to use (e.g. projects/PROJECT/locations/REGION/connectors/NAME). If not provided, one will be created."
  type        = string
  default     = null
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

variable "frontend_image" {
  description = "Docker image uri (with tag) for the frontend service"
  default = "europe-docker.pkg.dev/crmint-builds/crmint/frontend:latest"
}

variable "controller_image" {
  description = "Docker image uri (with tag) for the controller service"
  default = "europe-docker.pkg.dev/crmint-builds/crmint/controller:latest"
}

variable "jobs_image" {
  description = "Docker image uri (with tag) for the jobs service"
  default = "europe-docker.pkg.dev/crmint-builds/crmint/jobs:latest"
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
# Test utilities

variable "test_google_access_token" {
  type    = string
  default = null
}

variable "frontend_sa_email" {
  description = "Existing Service Account email for Frontend. If null, one will be created."
  type        = string
  default     = null
}

variable "jobs_sa_email" {
  description = "Existing Service Account email for Jobs. If null, one will be created."
  type        = string
  default     = null
}

variable "controller_sa_email" {
  description = "Existing Service Account email for Controller. If null, one will be created."
  type        = string
  default     = null
}

variable "pubsub_sa_email" {
  description = "Existing Service Account email for PubSub. If null, one will be created."
  type        = string
  default     = null
}
