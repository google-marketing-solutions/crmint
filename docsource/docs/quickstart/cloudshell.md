# CRMint Quickstart

1.  Install `crmint` command-line:

    ```shell
    $ curl -L https://raw.githubusercontent.com/dulacp/crmint/feature/install-script/scripts/install.sh | bash
    ```

1.  Congratulations, you have `crmint` command-line installed on your CloudShell. You can access it whenever you need to manage your CRMint instances.

    ```shell
    $ crmint --help
    ```

1.  Create a stage file for your first deployment:

    ```shell
    $ crmint stages create
    ```

1.  Setup your environment:

    ```shell
    $ crmint cloud setup
    ```

1.  Deploy your instance:

    ```shell
    $ crmint cloud deploy
    ```

1.  Once this script has completed executing, the installation is complete.

1.  <a href="https://console.cloud.google.com/appengine/services?project=crmint-dev-test">Open your CRMint application</a> with the default service.
