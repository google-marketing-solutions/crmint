locals {
  subscriptions = {
    "crmint-3-start-task" = {
      "endpoint" = "${google_cloud_run_service.jobs_run.status[0].url}/push/start-task",
      "ack_deadline_seconds" = 600,
      "minimum_backoff" = 60,  # seconds
    }

    "crmint-3-task-finished" = {
      "endpoint" = "${google_cloud_run_service.controller_run.status[0].url}/push/task-finished",
      "ack_deadline_seconds" = 60,
      "minimum_backoff" = 10,  # seconds
    }

    "crmint-3-start-pipeline" = {
      "endpoint" = "${google_cloud_run_service.controller_run.status[0].url}/push/start-pipeline",
      "ack_deadline_seconds" = 60,
      "minimum_backoff" = 10,  # seconds
    }
  }
}

resource "google_pubsub_topic" "topics" {
  for_each = local.subscriptions
  name = each.key
}

resource "google_pubsub_topic" "pipeline-finished" {
  name = "crmint-3-pipeline-finished"
}

resource "random_id" "pubsub_verification_token" {
  byte_length = 16
}

resource "google_pubsub_subscription" "subscriptions" {
  for_each = local.subscriptions

  name  = "${each.key}-subscription"
  topic = lookup(google_pubsub_topic.topics, each.key).id

  ack_deadline_seconds = each.value.ack_deadline_seconds
  expiration_policy {
    ttl = ""  # Stands for "never".
  }
  retry_policy {
    minimum_backoff = "${each.value.minimum_backoff}s"
  }

  push_config {
    oidc_token {
      audience              = google_iap_client.default.client_id
      service_account_email = google_service_account.pubsub_sa.email
    }

    push_endpoint = "${each.value.endpoint}?token=${random_id.pubsub_verification_token.b64_url}"
  }
}
