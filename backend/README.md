# Backend

## Build and update prod services

**Update the controller service**

```sh
$ REGION=europe-west1
$ IMAGE=europe-docker.pkg.dev/${PROJECT_ID}/crmint/controller

# Builds container image with latest code changes.
$ cd backend
$ gcloud builds submit \
    --region=${REGION} \
    --config cloudbuild.yaml \
    --substitutions _DOCKERFILE=controller.Dockerfile,_IMAGE_NAME=${IMAGE}

# Deploys the latest container image to Cloud Run.
$ gcloud run services update controller \
    --region europe-west1 \
    --image=${IMAGE}:latest

# (Optional) Run migrations with Terraform
$ cd terraform
$ terraform apply -target module.cli.null_resource.run_command[0]

# (Optional) Run migrations manually
$ gcloud builds submit \
    --region ${REGION} \
    --config ../backend/cloudmigrate.yaml \
    --no-source \
    --substitutions _IMAGE_NAME=${IMAGE}:latest,_INSTANCE_CONNECTION_NAME=${DB_CONN_NAME},_CLOUD_DB_URI=${DB_URI}
```

**Update the jobs service**

```sh
$ REGION=europe-west1
$ IMAGE=europe-docker.pkg.dev/${PROJECT_ID}/crmint/jobs

# Builds container image with latest code changes.
$ cd backend
$ gcloud builds submit \
    --region=${REGION} \
    --config cloudbuild.yaml \
    --substitutions _DOCKERFILE=jobs.Dockerfile,_IMAGE_NAME=${IMAGE}

# Deploys container image to Cloud Run.
$ gcloud run services update jobs \
    --region us-east1 \
    --image=${IMAGE}:latest
```
