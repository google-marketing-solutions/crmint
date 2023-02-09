locals {
  secured_domain = "crmint.${google_compute_global_address.default.address}.nip.io"
}

resource "google_compute_managed_ssl_certificate" "default" {
  name = "crmint-managed"

  managed {
    domains = [local.secured_domain]
  }
}
