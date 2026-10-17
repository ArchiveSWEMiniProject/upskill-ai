FROM node:20-alpine

WORKDIR /app

COPY package.json ./
COPY server.js ./

# The node image ships an unprivileged "node" user; do not run as root.
USER node

EXPOSE 3000

CMD ["node", "server.js"]
