FROM node:22-alpine

WORKDIR /app

ARG VITE_API_BASE_URL=http://localhost:8025
ARG VITE_APP_NAME="PDFCraft Internal Admin"
ARG VITE_APP_ENV=development

ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_APP_NAME=${VITE_APP_NAME}
ENV VITE_APP_ENV=${VITE_APP_ENV}

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 3035

CMD ["npm", "run", "dev"]
