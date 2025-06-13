# Build stage
FROM node:18-alpine as builder

# Add build arguments
ARG VITE_GATEWAY_URL
ENV VITE_GATEWAY_URL=$VITE_GATEWAY_URL

# Add environment variables for TypeScript
ENV NODE_ENV=production
ENV GENERATE_SOURCEMAP=false

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy source code and configuration files
COPY . .

# Ensure TypeScript types are installed
RUN npm i -D @types/node

# Build the application (this will run TSC and then Vite)
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

# Add configuration for serve
RUN echo '{"port": 3003, "public": ".", "rewrites": [{"source": "**", "destination": "/index.html"}]}' > serve.json

# Expose port 3003
EXPOSE 3003

# Start serve
CMD ["serve", "-s", ".", "-l", "3003"]
