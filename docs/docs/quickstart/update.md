# CRMint Update Guide

Please run each of these commands in your CloudShell terminal.

## Update your CRMint CLI and code base

1.  Switch to your home directory

    ```shell
    cd $HOME
    ```

1.  Update `crmint` command-line:

    ```shell
    source <(curl -Ls https://raw.githubusercontent.com/google/crmint/master/scripts/install.sh) master
    ```

1. Update your CRMint app:

    ```shell
    crmint bundle update
    ```
