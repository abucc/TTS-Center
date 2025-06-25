# Build stage
FROM node:18-alpine as builder

# Add build arguments
ARG VITE_GATEWAY_URL
ENV VITE_GATEWAY_URL=$VITE_GATEWAY_URL

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install all dependencies (including devDependencies for build)
# Don't set NODE_ENV=production during install to ensure devDependencies are installed
RUN npm install

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

# Install serve
RUN npm install -g serve

# Make sure environment variable is available at runtime
ARG VITE_GATEWAY_URL
ENV VITE_GATEWAY_URL=$VITE_GATEWAY_URL

# Copy built assets from builder stage
COPY --from=builder /app/dist .

# Add configuration for serve (SPA routing)
RUN echo '{"rewrites": [{"source": "**", "destination": "/index.html"}]}' > serve.json

# Expose port 3003
EXPOSE 3003

# Start serve
CMD ["serve", "-s", ".", "-l", "3003"]
