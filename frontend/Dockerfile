FROM node:22-alpine AS builder
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
# Type checking includes tests, which share the backend's story fixture.
COPY backend/tests/fixtures/branching_story.json /build/backend/tests/fixtures/branching_story.json
RUN npm run build

FROM nginx:stable-alpine AS runtime
COPY frontend/docker/nginx.conf /etc/nginx/nginx.conf
COPY --from=builder /build/frontend/dist /usr/share/nginx/html
USER nginx
EXPOSE 8080
ENTRYPOINT ["nginx"]
CMD ["-g", "daemon off;"]
