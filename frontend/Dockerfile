##
# Builder stage
#
FROM node:16.16 AS builder

WORKDIR /app

COPY package.json /app/package.json
RUN npm install

COPY . /app
RUN npm run build -- -c production

##
# Production stage
#
FROM nginx:stable
COPY --from=builder /app/dist/ /var/www
COPY ./nginx.conf /etc/nginx/conf.d/configfile.template
CMD sh -c "envsubst '\$PORT' < /etc/nginx/conf.d/configfile.template > /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"
