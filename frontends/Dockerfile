# Console produces static assets shared by both target architectures.
FROM --platform=$BUILDPLATFORM node:24-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
COPY apps/console/package.json apps/console/package.json
COPY apps/shortlink/package.json apps/shortlink/package.json
COPY packages/api-client/package.json packages/api-client/package.json
COPY packages/config/package.json packages/config/package.json

RUN npm ci

COPY . .

RUN npm run build:console


FROM nginx:1.27-alpine AS runtime

COPY apps/console/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/apps/console/dist /usr/share/nginx/html

EXPOSE 80
