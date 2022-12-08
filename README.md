# CRMint

**Make reliable data integration and data processing with Google easy for
advertisers.**

* [User Documentation](https://google.github.io/crmint)
* [Deploy Guide](https://github.com/google/crmint/wiki/Deploy-CRMint-on-Google-Cloud-Platform)
* [Contributor's Guide](https://github.com/google/crmint/wiki/Contributor's-Guide)
* [Wiki](https://github.com/google/crmint/wiki)


| Status | Coverage | Description |
| :----- | :--------- | :---------- |
| [![testing-cli](https://github.com/google/crmint/actions/workflows/testing-cli.yml/badge.svg?branch=master)](https://github.com/google/crmint/actions/workflows/testing-cli.yml) | [![codecov](https://codecov.io/gh/google/crmint/branch/master/graph/badge.svg?flag=cli)](https://codecov.io/gh/google/crmint) | Testing the reliability of our deployment tool |
| [![testing-backend](https://github.com/google/crmint/actions/workflows/testing-backend.yml/badge.svg?branch=master)](https://github.com/google/crmint/actions/workflows/testing-backend.yml) | [![codecov](https://codecov.io/gh/google/crmint/branch/master/graph/badge.svg?flag=backend)](https://codecov.io/gh/google/crmint) | Testing the core of CRMint backend engine |
| [![testing-frontend](https://github.com/google/crmint/actions/workflows/testing-frontend.yml/badge.svg?branch=master)](https://github.com/google/crmint/actions/workflows/testing-frontend.yml) | - | Testing our frontend |
| [![build-images](https://github.com/google/crmint/actions/workflows/build-images.yml/badge.svg?branch=master)](https://github.com/google/crmint/actions/workflows/build-images.yml) | - | Building docker images for our services |
| [![terraform-plan](https://github.com/google/crmint/actions/workflows/terraform.yml/badge.svg?branch=master)](https://github.com/google/crmint/actions/workflows/terraform.yml) | - | Testing our Terraform plan |

## Deploy CRMint

Follow the tutorial built into Cloud Shell:

[![Open in Cloud Shell](https://gstatic.com/cloudssh/images/open-btn.svg)](https://shell.cloud.google.com/cloudshell/editor?cloudshell_git_repo=https%3A%2F%2Fgithub.com%2Fgoogle%2Fcrmint&cloudshell_git_branch=master&cloudshell_tutorial=docs%2Fdocs%2Fquickstart%2Fcloudshell.md&show=terminal)

## Ambition

CRMint was created to make advertisers' data integration and processing easy,
even for people without software engineering background.

It has simple and intuitive web UI that allows users to create, edit, run,
and schedule data pipelines consisting of data transfer and data processing
jobs.

**This is not an official Google product.**
