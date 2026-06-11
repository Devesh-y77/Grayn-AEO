FROM node:18-alpine AS base

WORKDIR /app

# Dependencies
COPY package.json package-lock.json* ./
RUN npm install

# Copy source
COPY . .

# Build
RUN npm run build

# Expose port
EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["npm", "start"]
