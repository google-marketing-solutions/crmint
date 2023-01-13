# CRMint CLI

*Build a new docker image*
```
$ cd $HOME/crmint
$ DOCKER_BUILDKIT=1 docker build -t crmint-cli -f cli/Dockerfile .
```

*Run the CLI*
```
$ cd $HOME/crmint

# CloudShell stores gcloud config in a tmp directory at `\$CLOUDSDK_CONFIG`.
# But to also work on local environments we default to the user home config.
$ GCLOUD_CONFIG_PATH="${CLOUDSDK_CONFIG:-\$HOME/.config}"

# Runs the CLI
$ docker run --rm -it --net=host \
    -v $HOME/crmint/cli:/app/cli \
    -v $HOME/crmint/terraform:/app/terraform \
    -v $GCLOUD_CONFIG_PATH:/root/.config \
    crmint-cli:latest \
    crmint --help
```
