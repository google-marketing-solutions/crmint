#!/bin/bash

# read_image_metadata.sh - designed for Terraform External Data Source provider
# source: https://www.terraform.io/docs/providers/external/data_source.html

# Exit if any of the intermediate steps fail
set -e

function error_exit() {
  echo "$1" 1>&2
  exit 1
}

function check_deps() {
  test -f $(which jq) || error_exit "jq command not detected in path, please install it"
}

function parse_input() {
  eval "$(jq -r '@sh "export IMAGE_NAME=\(.image_name) IMAGE_TAG=\(.image_tag)"')"
  if [[ -z "${IMAGE_TAG}" ]]; then export IMAGE_TAG=latest; fi
}

function read_image_metadata() {
  export IMAGE_DIGEST=$(gcloud container images list-tags ${IMAGE_NAME} --filter tags:${IMAGE_TAG} --format="value(digest)")
}

function produce_output() {
  jq -n \
    --arg digest ${IMAGE_DIGEST} \
    '{"digest":$digest}'
}

check_deps
parse_input
read_image_metadata
produce_output
