# CRMint Quickstart

Please run each of these commands in your CloudShell terminal.

## Install the command-line

1.  Switch to your home directory

    ```shell
    cd $HOME
    ```

1.  Install `crmint` command-line:

    ```shell
    source <(curl -Ls https://raw.githubusercontent.com/google/crmint/master/scripts/install.sh) master
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

    > Once this command has completed the installation has finished but some
    > Cloud resources are still propagating across Google global infrastructure.

1.  Retrieve the UI url:

    ```shell
    crmint cloud url
    ```

    > This command will wait until the UI is ready to be opened.


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
