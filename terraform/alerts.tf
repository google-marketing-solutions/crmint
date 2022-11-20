resource "google_logging_metric" "pipeline_status" {
  name   = "crmint/pipeline_status"
  filter = "resource.type=cloud_run_revision AND jsonPayload.log_type=PIPELINE_STATUS"
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
      key         = "pipeline_status"
      value_type  = "STRING"
      description = "Pipeline status"
    }
    labels {
      key         = "message"
      value_type  = "STRING"
      description = "Error message"
    }
    display_name = "Pipeline Status Metric"
  }
  label_extractors = {
    "pipeline_id"     = "EXTRACT(jsonPayload.labels.pipeline_id)"
    "pipeline_status" = "EXTRACT(jsonPayload.labels.pipeline_status)"
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
      filter               = "metric.type=\"logging.googleapis.com/user/${google_logging_metric.pipeline_status.id}\" AND jsonPayload.labels.pipeline_status=failed"
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
#    alert_strategy {
#      notification_rate_limit {
#        period = ...
#      }
#    }
  }
  notification_channels = [google_monitoring_notification_channel.email.id]
}
