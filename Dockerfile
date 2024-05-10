FROM debian:bookworm-slim as builder

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    bzip2 \
    ca-certificates \
    curl \
    freetds-dev \
    gawk \
    git \
    libsqlite3-dev \
    libssl3 \
    libzip-dev \
    make \
    openssl \
    patch \
    sbcl \
    time \
    unzip \
    wget \
    cl-ironclad \
    cl-babel \
  && rm -rf /var/lib/apt/lists/*

COPY ./bin/pgloader /opt/src/pgloader

ARG DYNSIZE=16384

RUN mkdir -p /opt/src/pgloader/build/bin \
  && cd /opt/src/pgloader \
  && make DYNSIZE=$DYNSIZE clones save

FROM python:3

# Make compiled pgloader from 'builder' container available to main container
COPY --from=builder /opt/src/pgloader/build/bin/pgloader /usr/local/bin
ADD ./bin/pgloader/conf/freetds.conf /etc/freetds/freetds.conf

COPY requirements/common.txt requirements/common.txt
RUN pip install -U pip && pip install -r requirements/common.txt
RUN pip install zc.buildout

COPY ./api /app/api
COPY ./bin /app/bin
COPY wsgi.py /app/wsgi.py
WORKDIR /app

# Generate scripts from gtfsdb source
RUN buildout -c /app/bin/gtfsdb/buildout.cfg install prod

#RUN useradd njt
#USER njt

EXPOSE 8080

ENTRYPOINT ["bash", "/app/bin/run.sh"]