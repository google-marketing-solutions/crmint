---
bodyclass: docs
headline: CRMint solution
layout: docs
sidenav: doc-side-solutions-nav.html
title: CRMint solution
type: markdown
---

This document is a template for CRMint solutions

## Overview

A brief overview of the **business challenge** that the template solution solves.

## Prerequisites

This solution requires the following:

*   Google Analytics 360
*   A customer-base of N website visitors per month
*   A BigQuery dataset with a table containing the following text fields:
    *   **Date** (`Timestamp`) - *The date for which the counts apply*.
    *   **Apples** (`Integer`) - *The number of apples for the day*.
    *   **Cakes** (`Integer`) - *The number of cakes for the day*.
*   *Some other constraint*

## Setup

1.  Download the [template pipeline JSON](https://github.com/google/crmint/solutions/solution_name/pipeline.json) from the solution gallery on GitHub.

1.  If you have not already, create a CRMint instance using the [quickstart](../quickstart/) guide.

1.  Click **Import from template** and select the JSON file to create the new pipeline.

## Data pipeline configuration

The following variables must be configured for this solution. Click on the newly-created pipeline
then click **Edit** to access the variable configuration.


**Variable name**| **Description**
-----|-----
BQ\_PROJECT| The ID of the Google Cloud Project.
BQ\_DATASET| The Dataset to use.
BQ\_TABLE| The table to use. **Note the requirements for the fields above**.
WIDGETS| The number of widgets to use in the calculation. This should be a number between 1 and 10.
SHEEP| The number of sheep to count when entering sleep mode.

## Google Analytics configuration

Having created the pipeline and configured it as above, create the necessary properties in Google Analytics:

1.  Click on **Widgets** in the *Groovy cats* view.
1.  Select the desired number of widgets.
1.  Click **Save**.

## Verifying correct installation

Once set up, perform the following steps to verify a test execution of the pipeline:

1.  ....
1.  ....
1.  ....

Now inspect the logs in CRMint to check for any errors:

1.  ....

Confirm that the output can also be seen in Google Analytics:

1.  ....
