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

ARG NPM_REGISTRY=https://registry.npmmirror.com

# Install serve
RUN npm install -g serve --registry=$NPM_REGISTRY

# Make sure environment variable is available at runtime
ARG VITE_API_BASE
ENV VITE_API_BASE=$VITE_API_BASE

# Copy built assets from builder stage
COPY --from=builder /app/dist .

# Add configuration for serve (SPA routing)
RUN echo '{"rewrites": [{"source": "**", "destination": "/index.html"}]}' > serve.json

# Expose port 3003
EXPOSE 3003

# Start serve
CMD ["serve", "-s", ".", "-l", "3003"]
