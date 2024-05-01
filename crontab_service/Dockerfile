FROM alpine:latest

# Install curl
RUN apk update && apk add --no-cache curl

# Copy crontab from codebase to the container
COPY crontab /data/crontab
WORKDIR /data

# Run the contents of the crontab file into the crontab command
RUN crontab /data/crontab

CMD ["/usr/sbin/crond", "-f", "-d", "0"]