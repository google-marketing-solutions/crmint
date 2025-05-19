##
# Base stage
#
FROM node:16.16 AS base
LABEL maintainer="Your Name <you@example.com>"

WORKDIR /app

COPY package.json /app/package.json
COPY package-lock.json /app/package-lock.json
RUN npm ci

COPY . /app

##
# Development stage
#
FROM base AS dev
CMD npm run start -- --watch --hmr --live-reload --host 0.0.0.0 --port $PORT

##
# Builder stage
#
FROM base AS builder
RUN npm run build -- -c production

##
# Production stage
#
FROM nginx:stable AS prod
USER nginx
COPY --from=builder /app/dist/ /var/www
COPY ./nginx.conf /etc/nginx/conf.d/configfile.template
CMD sh -c "envsubst '\$PORT,\$APP_TITLE' < /etc/nginx/conf.d/configfile.template > /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"
