# Copyright 2020 Google Inc
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import os
from google.cloud import pubsub_v1


def setup_pubsub():  # pylint: disable=too-many-locals
  """Create CRMint's PubSub topics and subscriptions."""
  crmint_subscriptions = {
      'crmint-3-start-task': {
          'push_endpoint': 'http://jobs:8081/push/start-task',
          'ack_deadline_seconds': 600,
          'minimum_backoff': 60,  # seconds
      },
      'crmint-3-task-finished': {
          'push_endpoint': 'http://controller:8080/push/task-finished',
          'ack_deadline_seconds': 60,
          'minimum_backoff': 10,  # seconds
      },
      'crmint-3-start-pipeline': {
          'push_endpoint': 'http://controller:8080/push/start-pipeline',
          'ack_deadline_seconds': 60,
          'minimum_backoff': 10,  # seconds
      },
      'crmint-3-pipeline-finished': None,
  }
  project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
  publisher = pubsub_v1.PublisherClient()
  subscriber = pubsub_v1.SubscriberClient()
  with subscriber:
    project_path = f'projects/{project_id}'
    topics_iterator = publisher.list_topics(request={'project': project_path})
    topic_paths = [t.name for t in topics_iterator]
    for topic_id in crmint_subscriptions:
      topic_path = publisher.topic_path(project_id, topic_id)
      if topic_path not in topic_paths:
        publisher.create_topic(request={'name': topic_path})
      subscription = crmint_subscriptions[topic_id]
      if subscription is not None:
        subscriptions_iterator = publisher.list_topic_subscriptions(
            request={'topic': topic_path})
        subscription_paths = list(subscriptions_iterator)
        subscription_id = f'{topic_id}-subscription'
        subscription_path = subscriber.subscription_path(
            project_id, subscription_id)
        if subscription_path not in subscription_paths:
          push_config = pubsub_v1.types.PushConfig(
              push_endpoint=subscription['push_endpoint'])
          minimum_backoff = pubsub_v1.types.Duration(
              seconds=subscription['minimum_backoff'])
          retry_policy = pubsub_v1.types.RetryPolicy(
              minimum_backoff=minimum_backoff)
          subscriber.create_subscription(request={
              'name': subscription_path,
              'topic': topic_path,
              'push_config': push_config,
              'ack_deadline_seconds': subscription['ack_deadline_seconds'],
              'retry_policy': retry_policy,
          })


if __name__ == '__main__':
  setup_pubsub()
