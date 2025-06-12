# Build stage
FROM node:18-alpine as builder

# Add build arguments
ARG VITE_GATEWAY_URL
ENV VITE_GATEWAY_URL=$VITE_GATEWAY_URL

WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Production stage
FROM node:18-alpine

WORKDIR /app

# Install serve
RUN npm install -g serve

# Copy built assets from builder stage
COPY --from=builder /app/dist .

# Add configuration for serve
RUN echo '{"port": 3003, "public": ".", "rewrites": [{"source": "**", "destination": "/index.html"}]}' > serve.json

# Expose port 3003
EXPOSE 3003

# Start serve
CMD ["serve", "-s", ".", "-l", "3003"]
