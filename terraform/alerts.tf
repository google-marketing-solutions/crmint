resource "google_logging_metric" "pipeline_status_failed" {
  name   = "crmint/pipeline_status_failed"
  filter = "resource.type=cloud_run_revision AND jsonPayload.log_type=PIPELINE_STATUS AND jsonPayload.labels.pipeline_status=failed"
  metric_descriptor {
    metric_kind = "DELTA"
    value_type  = "INT64"
    unit        = "1"
    labels {
      key         = "pipeline_id"
      value_type  = "STRING"
      description = "Pipeline ID"
    }
    labels {
      key         = "message"
      value_type  = "STRING"
      description = "Error message"
    }
    display_name = "Pipeline Status Failed Metric"
  }
  label_extractors = {
    "pipeline_id"     = "EXTRACT(jsonPayload.labels.pipeline_id)"
    "message"         = "EXTRACT(jsonPayload.message)"
  }
}

resource "google_monitoring_notification_channel" "email" {
  display_name = "Email Notification Channel"
  type         = "email"
  labels = {
    email_address = var.notification_sender_email
  }
  force_delete = false
  enabled      = true
}

resource "google_monitoring_alert_policy" "notify_on_pipeline_status_failed" {
  display_name = "Pipeline Status Failed Alert Policy"
  enabled      = true
  combiner     = "OR"
  conditions {
    display_name = "Monitor pipeline errors"
    condition_threshold {
      filter               = "metric.type=\"logging.googleapis.com/user/${google_logging_metric.pipeline_status_failed.id}\" AND resource.type=cloud_run_revision"
      duration             = "60s"
      comparison           = "COMPARISON_GT"
      threshold_value      = 0.001
      trigger {
        count = 1
      }
      aggregations {
        alignment_period     = "60s"
        cross_series_reducer = "REDUCE_NONE"
        per_series_aligner   = "ALIGN_COUNT"
      }
    }
  }
  notification_channels = [google_monitoring_notification_channel.email.id]
}
