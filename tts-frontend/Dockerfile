# Build stage
FROM node:18-alpine as builder

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

# Expose port 3003 (matches docker-compose.yml)
EXPOSE 3003

# Start serve
CMD ["serve", "-s", ".", "-l", "3003"]
