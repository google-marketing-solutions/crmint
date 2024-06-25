# How to Contribute

We'd love to accept your patches and contributions to this project. There are
just a few small guidelines you need to follow.

## Contributor License Agreement

Contributions to this project must be accompanied by a Contributor License
Agreement. You (or your employer) retain the copyright to your contribution,
this simply gives us permission to use and redistribute your contributions as
part of the project. Head over to <https://cla.developers.google.com/> to see
your current agreements on file or to sign a new one.

You generally only need to submit a CLA once, so if you've already submitted one
(even if it was for a different project), you probably don't need to do it
again.

## Code reviews

All submissions, including submissions by project members, require review. We
use GitHub pull requests for this purpose. Consult
[GitHub Help](https://help.github.com/articles/about-pull-requests/) for more
information on using pull requests.

## Run local version of CRMint

**Run all services and open the frontend**

```sh
$ export GOOGLE_CLOUD_PROJECT=<PROJECT_ID>
$ FRONTEND_DOCKER_TARGET=dev docker-compose up --build

# Open your browser at http://localhost:4200
```

**(Optional) If you need to reset the state of pipelines**

```sh
$ docker compose run controller python -m flask reset-pipelines
```

**(Optional) If you are adding a new model or updating an existing model**

```sh
# Start with a clean slate.
$ docker-compose down --volumes
$ docker-compose run controller python -m flask db upgrade
# Create the migration file and update it's permissions.
$ docker-compose run controller python -m flask db migrate
$ sudo chown {username} backend/migrations/versions/{migrations_file}.py
$ sudo chgrp primarygroup backend/migrations/versions/{migrations_file}.py
$ sudo chmod 640 backend/migrations/versions/{migrations_file}.py
# Apply the schema migration to the database.
$ docker-compose run controller python -m flask db upgrade
# Re-Apply the seeds to ensure the settings page shows up properly.
$ docker-compose run controller python -m flask db-seeds
```

You can now edit files locally and the Flask services will reload appropriately.

## Running tests locally

Install the [act](https://github.com/nektos/act) tool to run Github Actions
locally (more details on the job names [options available to be used with -j]
can be found in the config files held within the .github/workflows directory).

### Run CLI Tests
```sh
$ act -j run-cli-tests --reuse --bind
```

### Run Backend Controller Tests
```sh
$ act -j run-controller-tests --reuse --bind
```

### Run Backend Jobs Tests
```sh
$ act -j run-jobs-tests --reuse --bind
```

### Run Frontend Tests
```sh
$ act -j run-frontend-tests --reuse --bind
```

### Updating Dependencies
#### CLI
Update dependencies in cli/setup.py then:
```sh
$ cd cli/
$ rm -rf build/
$ rm -rf crmint.egg-info/
$ python setup.py build
$ pip-compile --allow-unsafe --generate-hashes --resolver=backtracking setup.py
```

#### Backend
Update dependencies in requirements-controller.in and/or requirements-jobs.in then:
```sh
$ pip-compile --allow-unsafe --generate-hashes --resolver=backtracking backend/requirements-controller.in
$ pip-compile --allow-unsafe --generate-hashes --resolver=backtracking backend/requirements-jobs.in
```

## Deploy custom build on GCP

```sh
# Clones the repo
$ git clone https://github.com/google/crmint
# Installs the CRMint CLI (if not already available)
$ bash crmint/scripts/install.sh
# Checkouts your desired branch (if needed)
$ cd crmint
$ git checkout <your_branch>
# Builds and deploys everything
$ ./scripts/build_and_deploy.sh
```

## Community Guidelines

This project follows [Google's Open Source Community
Guidelines](https://opensource.google.com/conduct/).
