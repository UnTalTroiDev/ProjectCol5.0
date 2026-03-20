FROM node:20-slim

WORKDIR /app

# Install dependencies in a separate layer so Docker cache is reused when only
# source code changes.
COPY package.json package-lock.json* ./
RUN npm install

# Mount the rest of the source at runtime via a bind mount (docker-compose).
# The COPY here ensures the image is self-contained for standalone runs.
COPY . .

EXPOSE 5173

# --host exposes the dev server to 0.0.0.0 so it is reachable from the host
# and from other containers on the shared Docker network.
CMD ["npm", "run", "dev", "--", "--host"]
