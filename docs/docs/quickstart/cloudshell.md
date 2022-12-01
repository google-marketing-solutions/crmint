# CRMint Quickstart

Please run each of these commands in your CloudShell terminal.

## Install the command-line

1.  Switch to your home directory

    ```shell
    cd $HOME
    ```

1.  Install `crmint` command-line:

    ```shell
    bash <(curl -Ls https://raw.githubusercontent.com/google/crmint/master/scripts/install.sh) master
    ```

1.  Congratulations, you have `crmint` command-line installed on your CloudShell. You can access it whenever you need to manage your CRMint instances.

    ```shell
    crmint --help
    ```

## [Simple] Deploy CRMint with one command

_For advanced users, you move to the next section for more flexibility._

1.  Run this one command to deploy CRMint:

    ```shell
    crmint bundle install
    ```

1.  (Optional) Allow more users from your organization to access CRMint tool:

    ```shell
    crmint bundle allow-users email1,email2,email3
    ```

    > If these users are external to your organization, you will have an
    > additional step to modify your Consent Screen settings by
    > [making the user type as "External" in the Cloud Platform UI](https://console.cloud.google.com/apis/credentials/consent).
    > **You can only do it in the UI**.

1.  Open the CRMint UI link specified in the output of the previous command

    > You might need to wait for a few minutes after the initial deployment.

## [Advanced] Detailed deployment of CRMint

1.  Create a stage file for your GCP project:

    ```shell
    crmint stages create
    ```

    > This stage file contains a default configuration for your environment.
    > Feel free to customize it, you can see the documented list of variables
    > in `terraform/variables.tf`

1.  Run checks to validate that CRMint can be deployed:

    ```shell
    crmint cloud checklist
    ```

    > Once all the checks are passing you can safely move on the next command.

1.  Setup your environment:

    ```shell
    crmint cloud setup
    ```

    > Now your GCP project matches the specified Terraform configuration.

1.  Update the database schema:

    ```shell
    crmint cloud migrate
    ```

    > Once this script has completed executing, the installation is complete.

1.  (Optional) Allow more users from your organization to access CRMint tool:

    ```shell
    crmint bundle allow-users email1,email2,email3
    ```

    > If these users are external to your organization, you will have an
    > additional step to modify your Consent Screen settings by
    > [making the user type as "External" in the Cloud Platform UI](https://console.cloud.google.com/apis/credentials/consent).
    > **You can only do it in the UI**.

1.  Open the CRMint UI link specified in the output of the previous command

    > You might need to wait for a few minutes after the initial deployment.
