resource "google_cloud_scheduler_job" "heartbeat" {
  name        = "crmint-heartbeat"
  description = "Triggers scheduled pipeline runs."
  schedule    = "* * * * *"
  project     = var.project_id

  pubsub_target {
    topic_name = lookup(google_pubsub_topic.topics, "crmint-3-start-pipeline").id
    data       = base64encode("{\"pipeline_ids\": \"scheduled\"}")
    attributes = {
      start_time = 0
    }
  }
}
