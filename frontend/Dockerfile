##
# Base stage
#
FROM node:16.16 AS base

WORKDIR /app

COPY package.json /app/package.json
RUN npm install

COPY . /app

##
# Development stage
#
FROM base AS dev
CMD npm run start -- --watch --port $PORT

##
# Builder stage
#
FROM base AS builder
RUN npm run build -- -c production

##
# Production stage
#
FROM nginx:stable AS prod
COPY --from=builder /app/dist/ /var/www
COPY ./nginx.conf /etc/nginx/conf.d/configfile.template
CMD sh -c "envsubst '\$PORT,\$APP_TITLE' < /etc/nginx/conf.d/configfile.template > /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"
