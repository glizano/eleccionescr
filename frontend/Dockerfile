# Stage 1: Build
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

# Accept build argument for backend URL and set as environment variable
ARG PUBLIC_BACKEND_URL=http://localhost:8000
ENV PUBLIC_BACKEND_URL=${PUBLIC_BACKEND_URL}

RUN npm run build

# Stage 2: Serve
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
