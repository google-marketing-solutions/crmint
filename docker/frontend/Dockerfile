FROM node:10.11.0-alpine
MAINTAINER Pierre Dulac <dulacp@google.com>

# Copy the app files
WORKDIR /app
COPY ./frontend/ /app/frontend

# Start
WORKDIR /app/frontend
RUN apk add --no-cache --virtual .bootstrap-deps \
        git \
    && npm install \
    && apk del .bootstrap-deps

VOLUME ["/app/frontend"]

# START DEBUG with bash if needed
#RUN apk add --no-cache bash
# END DEBUG

EXPOSE 4200
CMD node_modules/@angular/cli/bin/ng serve --host 0.0.0.0
