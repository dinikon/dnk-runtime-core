FROM node:24-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
COPY apps/core/package.json apps/core/package.json
COPY apps/console/package.json apps/console/package.json
COPY apps/shortlink/package.json apps/shortlink/package.json
COPY packages/api-client/package.json packages/api-client/package.json
COPY packages/config/package.json packages/config/package.json
COPY packages/ui/package.json packages/ui/package.json
RUN npm ci --ignore-scripts
COPY . .
RUN npm run build:core

FROM node:24-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production
ENV HOST=0.0.0.0
ENV PORT=3000
COPY --from=build --chown=node:node /app/apps/core/.output ./.output
USER node
EXPOSE 3000
CMD ["node", ".output/server/index.mjs"]

FROM nginx:1.27-alpine AS gateway
COPY apps/core/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
