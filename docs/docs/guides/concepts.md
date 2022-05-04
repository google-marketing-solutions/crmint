---
bodyclass: docs
headline: What is CRMint?
layout: docs
sidenav: doc-side-guides-nav.html
title: Guides
type: markdown
---

## CRMint Concepts

The [overview guide](index.html) describes the purpose and general capabilities of CRMint. This document breaks CRMint down into its conceptual parts.

### Pipelines

At the heart of CRMint are pipelines. A pipeline is the largest component within CRMint, and is the end-to-end process by which a business task is achieved.

For example, a pipeline could be created to load conversion data into Google Analytics. The pipeline might perform many actions for example:

*   Load data from a CSV on Cloud Storage into BigQuery
*   Perform some transformations, using BigQuery
*   Send the resulting data to Google Analytics using the Measurement Protocol.

Pipelines can be executed manually, or more commonly run on a schedule.

### Jobs

Pipelines are divided into *jobs*. A job is a single discrete task performed by a *worker*.  Workers are re-usable building blocks that perform common actions such as loading data from one source to another, which can be composed into pipelines.

In the above example pipeline, the job of loading data into BigQuery would be performed by worker with *worker class* **StorageToBQImporter**.

Once the data is loaded into BigQuery, then the job for transforming the data can start. This secondary job therefore has a *job dependency* on the previous **StorageToBQImporter**-based job.

By defining jobs to perform each of the necessary tasks in the pipeline, and defining the job dependencies of each, the result is a graph that defines the execution path of the pipeline as a whole.

The full range of Workers can be seen in the [workers reference](../reference/worker_spec.html)

### Creating pipelines using the editor

The easiest way to create a pipeline is through the user interface on your CRMint instance.

Through the user interface, each component job can be defined in the pipeline, and a graph created by defining job dependencies.

The pipeline is customised by then defining variables and expressions as discussed [in the separate guide](variables.html).

### JSON pipeline configuration

In addition to creating pipelines using the editor, it is possible to work with pipelines in a JSON format.

This allows pipelines to be:

*   **Easily exported or imported**: The user interface provides the means to create a new pipeline from JSON, using the Import by template button. Equally, an existing pipeline can be exported using the Export button, to dowload as JSON.
*   **Replicated**: An exported pipeline could be imported to create a replica, then modified as required. Alternatively, advanced editing could be performed on the JSON prior to re-importing, for example, if all references to Acme Corp needed changing to Example Inc, in every part of the pipeline, this could be done with a search and replace in a text editor.
*   **Shared**, for example as an open-source template.

For details on the format of the pipeline JSON, see the [Pipeline JSON reference](../reference/index.html)

