# CRMint Quickstart

Please run each of these commands in your CloudShell terminal.

## Install the command-line

1.  Install `crmint` command-line:

    ```shell
    bash <(curl -Ls https://raw.githubusercontent.com/google/crmint/master/scripts/install.sh) master
    ```

1.  Congratulations, you have `crmint` command-line installed on your CloudShell. You can access it whenever you need to manage your CRMint instances.

    ```shell
    crmint --help
    ```

## Deploy your project

1.  Create a stage file for your first deployment:

    ```shell
    crmint stages create
    ```

    > This stage file contains all your environment variables for a particular deployment.

1.  Setup your environment:

    ```shell
    crmint cloud setup
    ```

    > Now your GCP project has all the required products activated and ready to go.

1.  Deploy your instance:

    ```shell
    crmint cloud deploy
    ```

    > Once this script has completed executing, the installation is complete.

1.  Open your CRMint application:

    ```shell
    gcloud app browse
    ```
