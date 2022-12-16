#!/bin/bash
#
# IPv6 is disabled in Google Cloud Shell, though the DNS resolution in Go
# does not always comply with this setting and from time to time resolves to
# an IPv6 address.
#
# The following workaround as been described proposes, waiting for the Go team
# to solve this properly (https://github.com/golang/go/issues/25321).
#
# See: https://github.com/hashicorp/terraform-provider-google/issues/6782
#

# Checks that we run inside a Google VM.
GMETADATA_ADDR=`dig +short metadata.google.internal`
if [[ "${GMETADATA_ADDR}" == "" ]]; then
  echo "Not on a Google VM, no need to patch the /etc/hosts file."
  exit 0
fi

# Backup existing /etc/hosts.
if [ ! -f /etc/hosts.backup ]; then
  sudo cp /etc/hosts /etc/hosts.backup
fi

read -r -d '' APIS << EOM
aiplatform.googleapis.com
analytics.googleapis.com
analyticsadmin.googleapis.com
analyticsreporting.googleapis.com
cloudbuild.googleapis.com
cloudresourcemanager.googleapis.com
cloudscheduler.googleapis.com
compute.googleapis.com
container.googleapis.com
googleapis.com
iam.googleapis.com
logging.googleapis.com
monitoring.googleapis.com
pubsub.googleapis.com
secretmanager.googleapis.com
servicenetworking.googleapis.com
sqladmin.googleapis.com
storage-api.googleapis.com
storage-component.googleapis.com
storage.googleapis.com
www.googleapis.com
EOM

# Restores the backup content.
sudo sh -c "cat /etc/hosts.backup > /etc/hosts"

# Adds IPv4 addresses for each Google Cloud API.
sudo sh -c "echo -e '\n# Forcing IPv4 to workaround a Go issue: https://github.com/golang/go/issues/25321' >> /etc/hosts"
for name in $APIS
do
  ipv4=$(getent ahostsv4 "$name" | head -n 1 | awk '{ print $1 }')
  sudo sh -c "echo '$ipv4 $name' >> /etc/hosts"
  echo "Forced IPv4 for $name: $ipv4"
done
