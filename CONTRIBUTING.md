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
# Creates a new migration.
$ docker compose run controller python -m flask db migrate
# Applies the schema migration to the database.
$ docker compose run controller python -m flask db upgrade
```

You can now edit files locally and the Flask services will reload appropriately.

## Running tests locally

Install the [act](https://github.com/nektos/act) tool to run Github Actions
locally.

```sh
$ act -j run-cli-tests --reuse --bind
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
