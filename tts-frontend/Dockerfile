# Build stage
FROM node:18-alpine as builder

# Add build arguments
ARG VITE_API_BASE
ARG NPM_REGISTRY=https://registry.npmmirror.com
ENV VITE_API_BASE=$VITE_API_BASE

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install all dependencies (including devDependencies for build)
# Don't set NODE_ENV=production during install to ensure devDependencies are installed
RUN npm ci --registry=$NPM_REGISTRY

# Set production environment after dependencies are installed
ENV NODE_ENV=production
ENV GENERATE_SOURCEMAP=false

# Copy source code and configuration files
COPY . .

# Build the application (Vite handles TypeScript compilation)
RUN npm run build

# Production stage
FROM node:18-alpine

WORKDIR /app

# Copy built assets and the lightweight static/proxy server
COPY --from=builder /app/dist /app
COPY server.js /server.js

EXPOSE 3003

CMD ["node", "/server.js"]
