FROM node:20-alpine as builder

WORKDIR /app

COPY frontend/package*.json ./
RUN npm install

COPY frontend/ .
RUN npm run build

FROM node:20-alpine

WORKDIR /app

COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/.next ./.next
COPY frontend/package*.json ./

RUN npm install --omit=dev

EXPOSE 3000

CMD ["npm", "start"]
