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

# (Optional) Run migrations manually
$ crmint cloud migrate
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
