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

variable "custom_domain" {
  description = <<EOF
    (Optional) Custom Domain for the UI (e.g. crmint.example.com).
    Leave this value empty to skip.
    EOF
  default     = ""
}

variable "iap_support_email" {
  description = "Support email used for configuring IAP"
}

variable "iap_allowed_users" {
  type = list
}
