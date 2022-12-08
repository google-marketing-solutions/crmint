resource "google_compute_global_address" "default" {
  name          = "global-crmint-default"
  address_type  = "EXTERNAL"
}

resource "google_compute_region_network_endpoint_group" "frontend_neg" {
  name                  = "frontend-neg"
  network_endpoint_type = "SERVERLESS"
  region                = var.region
  cloud_run {
    service = google_cloud_run_service.frontend_run.name
  }
}

resource "google_compute_region_network_endpoint_group" "controller_neg" {
  name                  = "controller-neg"
  network_endpoint_type = "SERVERLESS"
  region                = var.region
  cloud_run {
    service = google_cloud_run_service.controller_run.name
  }
}

resource "google_compute_region_network_endpoint_group" "jobs_neg" {
  name                  = "jobs-neg"
  network_endpoint_type = "SERVERLESS"
  region                = var.region
  cloud_run {
    service = google_cloud_run_service.jobs_run.name
  }
}

resource "google_compute_backend_service" "frontend_backend" {
  name                            = "crmint-frontend-backend-service"
  enable_cdn                      = false
  connection_draining_timeout_sec = 10

  backend {
    group = google_compute_region_network_endpoint_group.frontend_neg.id
  }

  iap {
    oauth2_client_id = google_iap_client.default.client_id
    oauth2_client_secret = google_iap_client.default.secret
  }

  load_balancing_scheme = "EXTERNAL"
  protocol              = "HTTP"
}

resource "google_compute_backend_service" "controller_backend" {
  name                            = "crmint-controller-backend-service"
  enable_cdn                      = false
  connection_draining_timeout_sec = 10

  backend {
    group = google_compute_region_network_endpoint_group.controller_neg.id
  }

  iap {
    oauth2_client_id = google_iap_client.default.client_id
    oauth2_client_secret = google_iap_client.default.secret
  }

  load_balancing_scheme = "EXTERNAL"
  protocol              = "HTTP"
}

resource "google_compute_backend_service" "jobs_backend" {
  name                            = "crmint-jobs-backend-service"
  enable_cdn                      = false
  connection_draining_timeout_sec = 10

  backend {
    group = google_compute_region_network_endpoint_group.jobs_neg.id
  }

  iap {
    oauth2_client_id = google_iap_client.default.client_id
    oauth2_client_secret = google_iap_client.default.secret
  }

  load_balancing_scheme = "EXTERNAL"
  protocol              = "HTTP"
}

resource "google_compute_url_map" "default" {
  name             = "crmint-http-lb"
  default_service  = google_compute_backend_service.frontend_backend.id

  host_rule {
    hosts        = ["*"]
    path_matcher = "allpaths"
  }

  path_matcher {
    name = "allpaths"
    default_service = google_compute_backend_service.frontend_backend.id

    path_rule {
      service = google_compute_backend_service.jobs_backend.id
      paths = ["/api/workers", "/api/workers/*", "/push/start-task"]
    }

    path_rule {
      service = google_compute_backend_service.controller_backend.id
      paths = ["/api/*", "/push/task-finished", "/push/start-pipeline"]
    }
  }
}

resource "google_compute_target_https_proxy" "default" {
  name    = "crmint-default-https-lb-proxy"
  url_map = google_compute_url_map.default.id
  ssl_certificates = [
    google_compute_managed_ssl_certificate.default.id,
    google_compute_ssl_certificate.locally_signed.id,
  ]
}

resource "google_compute_global_forwarding_rule" "default" {
  name = "crmint-default-https-lb-forwarding-rule"
  ip_protocol = "TCP"
  load_balancing_scheme = "EXTERNAL"
  port_range = "443"
  target = google_compute_target_https_proxy.default.id
  ip_address = google_compute_global_address.default.id
}

##
# Virtual Private Cloud

resource "google_compute_network" "private" {
  provider = google-beta
  count = var.use_vpc ? 1 : 0

  name                    = "crmint-private-network"
  project                 = var.network_project_id != null ? var.network_project_id : var.project_id
  routing_mode            = "REGIONAL"
  mtu                     = 1460
  auto_create_subnetworks = false  # Custom Subnet Mode

  # Create a network only if the compute.googleapis.com API has been activated.
  depends_on = [google_project_service.apis]
}

resource "google_compute_global_address" "db_private_ip_address" {
  provider = google-beta
  count = var.use_vpc ? 1 : 0

  name          = "crmint-db-private-ip-address"
  project       = var.network_project_id != null ? var.network_project_id : var.project_id
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  address       = "192.168.0.0"
  prefix_length = 16
  network       = google_compute_network.private[count.index].id
}

resource "google_service_networking_connection" "private_vpc_connection" {
  provider = google-beta
  count = var.use_vpc ? 1 : 0

  network                 = google_compute_network.private[count.index].id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.db_private_ip_address[count.index].name]
}

resource "google_compute_subnetwork" "private" {
  count = var.use_vpc ? 1 : 0

  name          = "crmint-private-subnetwork"
  ip_cidr_range = "10.8.0.0/28"
  region        = var.network_region != null ? var.network_region : var.region
  network       = google_compute_network.private[count.index].id
}

resource "google_vpc_access_connector" "connector" {
  provider       = google-beta
  count = var.use_vpc ? 1 : 0

  name           = "crmint-vpc-conn"
  machine_type   = "e2-micro"
  max_instances  = 3
  min_instances  = 2
  project        = var.network_project_id != null ? var.network_project_id : var.project_id
  region         = var.network_region != null ? var.network_region : var.region

  subnet {
    name = google_compute_subnetwork.private[count.index].name
    project_id = var.network_project_id != null ? var.network_project_id : var.project_id
  }

  depends_on = [google_project_service.vpcaccess]
}
