# Stage 1: Compile and Build angular codebase
# Use official node image as the base image
FROM node:16 as build
# Set the working directory
WORKDIR /usr/local/app
# Add the source code to app

COPY package.json /usr/local/app/
# Install all the dependencies
RUN npm install --legacy-peer-deps --force

ADD src /usr/local/app/src
#copy prod config
#COPY src/environments/environment.prod.ts src/environments/environment.ts
COPY tslint.json tsconfig.json tsconfig.app.json angular.json package.json /usr/local/app/

# Generate the build of the application
RUN npm run buildProd

# Stage 2: Serve app with nginx server
# Use official nginx image as the base image
FROM nginx:1.21.3
# Copy the build output to replace the default nginx contents.
COPY --from=build /usr/local/app/dist /app/
# Exposure of ports will be done in docker-compose.yml
COPY nginx.conf /etc/nginx/nginx.conf
