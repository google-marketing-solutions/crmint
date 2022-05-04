---
bodyclass: docs
layout: docs
title: Deploy CRMint Quickstart
headline: Deploy CRMint Quickstart
sidenav: doc-side-quickstart-nav.html
type: markdown
---
<p class="lead">This guide gets you started with CRMint, with a basic deployment to Google Cloud.</p>

<div id="toc"></div>

## Before you begin

### Prerequisites

*   About 25 mins of time.
*   A Google Account, for use on the Google Cloud Platform.

## Create a project on Google Cloud

1.  <a href="https://console.cloud.google.com/projectcreate" target="_blank">Create a new project</a> on Google Cloud.

    Whilst this is created, a progress spinner can be seen in the top right task bar.

1.  Once the spinner has stopped, click on the notification to select the newly-created project. Enter the project ID here:

    <input id="project-id" placeholder="Insert Project ID here, e.g. flying-tiger-112301" data-target-id="cloudshell-url">

## Run setup steps on Cloud Shell

1.  Open a Cloud Shell

    <a id='cloudshell-url' class="gray-image" target="_blank" data-href="https://console.cloud.google.com/cloudshell/editor?project=placeholder&cloudshell_git_repo=https%3A%2F%2Fgithub.com%2Fgoogle%2Fcrmint&cloudshell_git_branch=master&&cloudshell_tutorial=docsource%2Fdocs%2Fquickstart%2Fcloudshell.md&cloudshell_open_in_editor=README.md">
    <img alt="Open in Cloud Shell" src ="https://gstatic.com/cloudssh/images/open-btn.svg" style="width:250px;"></a>

1.  Follow the <a href="cloudshell.md" target="_blank">instructions</a> which appear in the tutorial within the Cloud Shell environment, on the right side-panel.

1.  Once this script has completed executing, CRMint has been installed!

## Verifying the installation

1.  Launch the CRMint Application on your newly-created instance at: <a href="https://xxxxxx.appspot.com" id="crm-launch" target="_blank">&lt;Project ID not set&gt;</a>

1.  You should see a CRMint control panel, showing no pipelines.

1.  Congratulations, you're all set to start exploring CRMint!

## What's next

- Read a full explanation of how CRMint works in [What is CRMint?](../guides/)
  and [CRMint Concepts](../guides/concepts.html)
- CRMint pipeline concepts
- [Create your first CRMint pipeline with BigQuery ML](../quickstart/tutorial.html)
