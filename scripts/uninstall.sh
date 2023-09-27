#!/bin/bash
#
# Copyright 2023 Google Inc
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

# CRMint Uninstall Script
#
# Removes all resources associated with the Cloud Run version of CRMint.
# Execute this script as: bash $HOME/crmint/scripts/uninstall.sh

function execute_command() {
    DESCRIPTION=$1
    COMMAND=$2

    echo "Attempting: $DESCRIPTION"
    eval "$COMMAND"
    
    # Check the exit status
    if [ $? -eq 0 ]; then
        echo "$DESCRIPTION - Completed successfully."
    else
        echo "$DESCRIPTION - Encountered an error."
    fi
    echo "-----------------------------------"
}

CURRENT_REGION=$(gcloud sql instances describe crmint-3-db --format="value(region)")

if [ -z "$CURRENT_REGION" ]; then
    CURRENT_REGION="us-central1"
fi

echo "We detected your region as: $CURRENT_REGION"
read -p "Do you want to continue with this region? (yes/no) " RESPONSE

if [[ ! "$RESPONSE" =~ ^[Yy][Ee][Ss]$ ]]; then
    echo "Please enter the region:"
    read REGION
else
    REGION=$CURRENT_REGION
fi

PROJECT_ID=$(gcloud config list --format 'value(core.project)')
echo "Your current project ID is set to: $PROJECT_ID"
read -p "Do you want to continue with this project ID? (yes/no) " PROJECT_RESPONSE

if [[ ! "$PROJECT_RESPONSE" =~ ^[Yy][Ee][Ss]$ ]]; then
    echo "Please enter the project ID:"
    read PROJECT_ID
fi

# SQL
execute_command "Delete SQL database" "gcloud sql instances delete crmint-3-db --quiet"

# VPC
execute_command "Delete VPC connector" "gcloud compute networks vpc-access connectors delete crmint-vpc-conn --region=$REGION --quiet"
execute_command "Delete network peering" "gcloud compute networks peerings delete servicenetworking-googleapis-com --network=crmint-private-network"

# Addresses and related resources
execute_command "Delete global address" "gcloud compute addresses delete global-crmint-default --global --quiet"
execute_command "Delete private IP address" "gcloud compute addresses delete crmint-db-private-ip-address --global"
execute_command "Delete forwarding rule" "gcloud compute forwarding-rules delete crmint-default-https-lb-forwarding-rule --global --quiet"
execute_command "Delete subnetwork" "gcloud compute networks subnets delete crmint-private-subnetwork --region=$REGION --quiet"

# Cloud Run services
execute_command "Delete controller service" "gcloud run services delete controller --region=$REGION --quiet"
execute_command "Delete jobs service" "gcloud run services delete jobs --region=$REGION --quiet"
execute_command "Delete frontend service" "gcloud run services delete frontend --region=$REGION --quiet"

execute_command "Delete private network" "gcloud compute networks delete crmint-private-network --quiet"

# PubSub resources
execute_command "Delete start-pipeline subscription" "gcloud pubsub subscriptions delete crmint-3-start-pipeline-subscription --quiet"
execute_command "Delete start-task subscription" "gcloud pubsub subscriptions delete crmint-3-start-task-subscription --quiet"
execute_command "Delete task-finished subscription" "gcloud pubsub subscriptions delete crmint-3-task-finished-subscription --quiet"
execute_command "Delete pipeline-finished topic" "gcloud pubsub topics delete crmint-3-pipeline-finished --quiet"
execute_command "Delete start-pipeline topic" "gcloud pubsub topics delete crmint-3-start-pipeline --quiet"
execute_command "Delete start-task topic" "gcloud pubsub topics delete crmint-3-start-task --quiet"
execute_command "Delete task-finished topic" "gcloud pubsub topics delete crmint-3-task-finished --quiet"

# HTTPS, SSL, and related resources
execute_command "Delete https proxy" "gcloud compute target-https-proxies delete crmint-default-https-lb-proxy --quiet"
execute_command "Delete SSL certificate" "gcloud compute ssl-certificates delete crmint-managed --quiet"
execute_command "Delete URL map" "gcloud compute url-maps delete crmint-http-lb --global --quiet"
execute_command "Delete backend service for controller" "gcloud compute backend-services delete crmint-controller-backend-service --global --quiet"
execute_command "Delete backend service for jobs" "gcloud compute backend-services delete crmint-jobs-backend-service --global --quiet"
execute_command "Delete backend service for frontend" "gcloud compute backend-services delete crmint-frontend-backend-service --global --quiet"

# Network endpoint groups
execute_command "Delete controller NEG" "gcloud compute network-endpoint-groups delete controller-neg --region=$REGION --quiet"
execute_command "Delete jobs NEG" "gcloud compute network-endpoint-groups delete jobs-neg --region=$REGION --quiet"
execute_command "Delete frontend NEG" "gcloud compute network-endpoint-groups delete frontend-neg --region=$REGION --quiet"

# Secrets, IAP Oauth and scheduler jobs
execute_command "Delete secret" "gcloud secrets delete cloud_db_uri"
# Iterating over OAUTH clients
for client in $OAUTH_CLIENTS_TO_DELETE; do
  execute_command "Delete OAuth client $client" "gcloud iap oauth-clients delete $client --quiet"
done
execute_command "Delete scheduler job" "gcloud scheduler jobs delete crmint-heartbeat --location=$REGION --quiet"

# Monitoring policies
for policy_id in $(gcloud alpha monitoring policies list 2>&1 | grep -o "projects/$PROJECT_ID/alertPolicies/[0-9]*" | sort | uniq); do
  execute_command "Delete monitoring policy $policy_id" "gcloud alpha monitoring policies delete \"$policy_id\" --quiet"
done

# Logging metrics
execute_command "Delete logging metric" "gcloud logging metrics delete crmint/pipeline_status_failed --quiet"

# Service accounts
execute_command "Delete controller service account" "gcloud iam service-accounts delete crmint-controller-sa@$PROJECT_ID.iam.gserviceaccount.com --quiet"
execute_command "Delete frontend service account" "gcloud iam service-accounts delete crmint-frontend-sa@$PROJECT_ID.iam.gserviceaccount.com --quiet"
execute_command "Delete jobs service account" "gcloud iam service-accounts delete crmint-jobs-sa@$PROJECT_ID.iam.gserviceaccount.com --quiet"
execute_command "Delete pubsub service account" "gcloud iam service-accounts delete crmint-pubsub-sa@$PROJECT_ID.iam.gserviceaccount.com --quiet"

IAP_BRAND_ID=$(gcloud iap oauth-brands list | grep -o 'brands/[^ ]*' | cut -d'/' -f2)
echo "The extracted IAP Brand ID is: $IAP_BRAND_ID"
echo "If you are planning to redeploy CRMint on Cloud Run, update the iap_brand_id with this value ($IAP_BRAND_ID) in crmint/cli/stages/$PROJECT_ID.tfvars.json"

echo "Make sure your consent screen is set to internal (this can be changed again after the re-install). Please visit: https://console.cloud.google.com/apis/credentials/consent"

echo "To begin CRMint reinstallation run this command: source <(curl -Ls https://raw.githubusercontent.com/google-marketing-solutions/crmint/master/scripts/install.sh) master"
