FROM python:3.10-slim-bullseye

# Installs building tools.
RUN apt-get update \
    && apt-get -y install curl dnsutils unzip \
    # Clean up
    && apt-get autoremove -y \
    && apt-get clean -y \
    && rm -rf /var/lib/apt/lists/*

# Avoids warnings by switching to noninteractive.
ENV GCLOUD_SDK_VERSION=412.0.0 \
    TERRAFORM_VERSION=1.3.7 \
    PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    DEBIAN_FRONTEND=noninteractive

# Installs the gcloud command.
ENV PATH /google-cloud-sdk/bin:$PATH
RUN curl -O https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-sdk-${GCLOUD_SDK_VERSION}-linux-x86_64.tar.gz \
    && tar xzf google-cloud-sdk-${GCLOUD_SDK_VERSION}-linux-x86_64.tar.gz \
    && rm google-cloud-sdk-${GCLOUD_SDK_VERSION}-linux-x86_64.tar.gz \
    && ln -s /lib /lib64 \
    && gcloud config set core/disable_usage_reporting true \
    && gcloud config set component_manager/disable_update_check false
    #&& gcloud components install kubectl

# Installs Terraform.
RUN curl -O https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip \
  && unzip terraform_${TERRAFORM_VERSION}_linux_amd64.zip \
  && mv terraform /usr/bin \
  # Clean up
  && rm terraform_${TERRAFORM_VERSION}_linux_amd64.zip \
  && rm -rf /tmp/* \
  && rm -rf /var/lib/apt/lists/* \
  && rm -rf /var/cache/apk/* \
  && rm -rf /var/tmp/*

# Installs other tools needed by our CLI.
RUN apt-get update \
    && apt-get -y install --no-install-recommends apt-utils 2>&1 \
    && apt-get -y install git jq \
    # Clean up
    && apt-get autoremove -y \
    && apt-get clean -y \
    && rm -rf /var/lib/apt/lists/*

# Creates a virtualenv and activate it
ENV VIRTUAL_ENV=/opt/venv
RUN python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Installs CRMint CLI dependencies.
COPY cli /app/cli/
RUN pip install --require-hashes -r /app/cli/requirements.txt

# Installs CRMint CLI.
# NOTE: put the python egg into another directory than CLI so that we can
#       bind the local `cli` directory and do some local development.
ENV PYTHONPATH /app/cli:$PYTHONPATH
RUN mkdir -p /app/eggs
RUN cd /app/eggs && python /app/cli/setup.py develop

WORKDIR /app
CMD /bin/bash
