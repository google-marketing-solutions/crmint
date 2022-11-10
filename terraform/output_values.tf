output "frontend_url" {
  value       = "https://${tls_cert_request.default.dns_names[0]}"
  description = "The url to access CRMint UI."
}
