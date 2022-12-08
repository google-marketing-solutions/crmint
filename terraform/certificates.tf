locals {
  unsecured_domain = "crmint-unsecured.${google_compute_global_address.default.address}.nip.io"
  secured_domain = "crmint.${google_compute_global_address.default.address}.nip.io"
}

resource "tls_private_key" "root" {
  algorithm = "RSA"
  rsa_bits  = 2048
}

resource "tls_self_signed_cert" "root" {
  is_ca_certificate = true
  private_key_pem = tls_private_key.root.private_key_pem

  subject {
    common_name = "CRMint Personal Root"
    organization = "CRMint OpenSource"
  }

  validity_period_hours = 8760  # 1 year

  allowed_uses = [
    "cert_signing",
    "crl_signing",
    "digital_signature",
  ]
}

resource "tls_private_key" "default" {
  algorithm   = "ECDSA"
  ecdsa_curve = "P256"
}

resource "tls_cert_request" "default" {
  private_key_pem = tls_private_key.default.private_key_pem

  # Subject Alternative Name DNS entries
  dns_names = [local.unsecured_domain]

  # Subject Alternative Name IP entries
  ip_addresses = [google_compute_global_address.default.address]

  subject {
    common_name = local.unsecured_domain
    organization = "CRMint OpenSource"
  }
}

resource "tls_locally_signed_cert" "default" {
  cert_request_pem   = tls_cert_request.default.cert_request_pem
  ca_private_key_pem = tls_self_signed_cert.root.private_key_pem
  ca_cert_pem        = tls_self_signed_cert.root.cert_pem

  validity_period_hours = 8760  # 1 year

  allowed_uses = [
    "key_encipherment",
    "digital_signature",
    "client_auth",
    "server_auth",
  ]
}

resource "google_compute_ssl_certificate" "locally_signed" {
  name = "crmint-self-signed-with-chain"
  description = "Self managed certificate"

  private_key = tls_private_key.default.private_key_pem
  certificate = join(
    "\n",
    [
      trimspace(tls_locally_signed_cert.default.cert_pem),
      trimspace(tls_self_signed_cert.root.cert_pem),
    ]
  )

  lifecycle {
    create_before_destroy = true
  }
}

resource "google_compute_managed_ssl_certificate" "default" {
  name = "crmint-managed"

  managed {
    domains = [local.secured_domain]
  }
}
