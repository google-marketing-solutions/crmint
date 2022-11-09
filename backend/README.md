# Backend

## Build and update prod services

**Update the controller service**

```sh
$ cd backend
$ gcloud builds submit --region=us-east1 --config controller_cloudbuild.yaml
$ gcloud run services update controller \
    --region us-east1 \
    --image=us-docker.pkg.dev/${PROJECT_ID}/crmint/controller:latest
```

**Update the jobs service**

```sh
$ cd backend
$ gcloud builds submit --region=us-east1 --config jobs_cloudbuild.yaml
$ gcloud run services update jobs \
    --region us-east1 \
    --image=us-docker.pkg.dev/${PROJECT_ID}/crmint/jobs:latest
```
