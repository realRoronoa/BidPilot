FROM node:18-alpine AS build

WORKDIR /app

COPY package.json yarn.lock ./
RUN yarn install --frozen-lockfile || yarn install

COPY . .

ARG REACT_APP_BACKEND_URL
ENV REACT_APP_BACKEND_URL=$REACT_APP_BACKEND_URL

RUN yarn build

FROM node:18-alpine

WORKDIR /app
RUN npm install -g serve

COPY --from=build /app/build ./build

ENV PORT=3000
EXPOSE 3000

CMD ["sh", "-c", "serve -s build -l ${PORT:-3000}"]
