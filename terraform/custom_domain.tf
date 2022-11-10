# Creates a managed SSL certificate for your custom domain.

resource "google_compute_managed_ssl_certificate" "custom_domain" {
  count = length(var.custom_domain) > 0 ? 1 : 0

  name = "crmint-custom-domain"

  managed {
    domains = [
      var.custom_domain
    ]
  }
}

# Creates a separate load balancer for your custom domain.

resource "google_compute_global_address" "custom_domain" {
  count = length(var.custom_domain) > 0 ? 1 : 0

  name          = "global-crmint-custom-domain"
  address_type  = "EXTERNAL"
}

resource "google_compute_target_https_proxy" "custom_domain" {
  count = length(var.custom_domain) > 0 ? 1 : 0

  name    = "crmint-custom-https-lb-proxy"
  url_map = google_compute_url_map.default.id
  ssl_certificates = [google_compute_managed_ssl_certificate.custom_domain[count.index].id]
}

resource "google_compute_global_forwarding_rule" "custom_domain" {
  count = length(var.custom_domain) > 0 ? 1 : 0

  name = "crmint-custom-https-lb-forwarding-rule"
  ip_protocol = "TCP"
  load_balancing_scheme = "EXTERNAL"
  port_range = "443"
  target = google_compute_target_https_proxy.custom_domain[count.index].id
  ip_address = google_compute_global_address.custom_domain[count.index].id
}

# Binds your custom domain to the new external ip-address.

resource "google_project_service" "dns_service" {
  count = length(var.custom_domain) > 0 ? 1 : 0
  project = var.project_id
  service = "dns.googleapis.com"
}

resource "google_dns_managed_zone" "custom_domain" {
  count = length(var.custom_domain) > 0 ? 1 : 0

  name        = replace(var.custom_domain, ".", "-")
  dns_name    = "${var.custom_domain}."
  description = "Test DNS zone for our Instant BQML Demo environment"

  visibility = "public"

  dnssec_config {
    kind          = "dns#managedZoneDnsSecConfig"
    non_existence = "nsec3"
    state         = "on"

    default_key_specs {
      algorithm  = "rsasha256"
      key_length = 2048
      key_type   = "keySigning"
      kind       = "dns#dnsKeySpec"
    }
    default_key_specs {
      algorithm  = "rsasha256"
      key_length = 1024
      key_type   = "zoneSigning"
      kind       = "dns#dnsKeySpec"
    }
  }
}

resource "google_dns_record_set" "frontend" {
  count = length(var.custom_domain) > 0 ? 1 : 0

  name = google_dns_managed_zone.custom_domain[count.index].dns_name
  type = "A"
  ttl  = 300

  managed_zone = google_dns_managed_zone.custom_domain[count.index].name

  rrdatas = [google_compute_global_address.custom_domain[count.index].address]
}
