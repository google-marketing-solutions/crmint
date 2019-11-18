# CRMint

**Make reliable data integration and data processing with Google easy for
advertisers.**

* [User Documentation](https://google.github.io/crmint)
* [Deploy Guide](https://github.com/google/crmint/wiki/Deploy-CRMint-on-Google-Cloud-Platform)
* [Contributor's Guide](https://github.com/google/crmint/wiki/Contributor's-Guide)
* [Wiki](https://github.com/google/crmint/wiki)


| Status | Coverage | Branch | Description |
| :----- | :--------- | :----- | :---------- |
| [![Build Status](https://travis-ci.org/google/crmint.svg?branch=dev)](https://travis-ci.org/google/crmint) | - | [dev](https://github.com/google/crmint/tree/dev) | Latest build, use it at your own risks  |
| [![Build Status](https://travis-ci.org/google/crmint.svg?branch=master)](https://travis-ci.org/google/crmint) | - | [master](https://github.com/google/crmint/tree/master) | Production ready releases |

> You can have data without information, but you cannot have information
> without data.
>
> — _Daniel Keys Moran_

CRMint was created to make advertisers' data integration and processing easy,
even for people without software engineering background.

CRMint has simple and intuitive web UI that allows users to create, edit, run,
and schedule data pipelines consisting of data transfer and data processing
jobs.

> This README is for building and extending CRMint as a developer. For guidance
> on using CRMint, refer to the [User documentation](https://google.github.io/crmint)

CRMint is a [Google App Engine](https://cloud.google.com/appengine/) application
written in Python for [Google App Engine Python Standard
Environment](https://cloud.google.com/appengine/docs/standard/python/). CRMint
uses [Cloud SQL](https://cloud.google.com/sql/) to store it's business data, and
[Stackdriver Logging](https://cloud.google.com/logging/) to store it's activity
logs.

Deploy CRMint to your [Google Cloud project](https://console.cloud.google.com/),
build a data pipeline, and benefit from data integration and processing in
[Google Cloud](https://cloud.google.com/).

**This is not an official Google product.**
