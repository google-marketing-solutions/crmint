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

**Initialize the local database**

```sh
$ docker-compose run controller python -m flask db upgrade
$ docker-compose run controller python -m flask db-seeds
$ docker-compose run controller python -m python setup_pubsub.py
```

**Run all services and open the frontend**

```sh
$ docker-compose up
$ open http://localhost:4200
```

You can now edit files locally and the Flask services will reload appropriately.

## Running tests locally

Install the [act](https://github.com/nektos/act) tool to run Github Actions
locally.

```sh
$ act -j run-cli-tests --reuse --bind
```

## Community Guidelines

This project follows [Google's Open Source Community
Guidelines](https://opensource.google.com/conduct/).
