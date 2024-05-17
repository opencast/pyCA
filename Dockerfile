FROM docker.io/library/alpine:3.19 AS base
RUN apk --no-cache --virtual .run-deps add \
      libcurl \
      postgresql-libs \
      py3-pip \
      python3
RUN apk --no-cache --virtual .build-deps add \
      curl-dev \
      g++ \
      gcc \
      linux-headers \
      make \
      musl-dev \
      nodejs \
      npm \
      postgresql-dev \
      python3-dev
RUN pip install --break-system-packages \
      gunicorn \
      psycopg2


FROM base as build-pyca
WORKDIR /usr/local/src
COPY requirements.txt package.json package-lock.json ./
RUN pip install --break-system-packages -r requirements.txt
RUN npm i
COPY . .
RUN make pypi


FROM base as build

COPY --from=build-pyca /usr/local/src/dist/pyca-*.tar.gz /tmp/pyca.tar.gz
RUN pip install --break-system-packages \
      /tmp/pyca.tar.gz
RUN apk del .build-deps \
 && rm /tmp/pyca.tar.gz


FROM docker.io/library/alpine:3.19 AS build-ffmpeg
ARG TARGETARCH
ARG FFMPEG_VERSION=release
RUN apk add --no-cache \
      curl \
      tar \
      xz \
 && mkdir -p /tmp/ffmpeg \
 && cd /tmp/ffmpeg \
 && curl -sSL "https://s3.opencast.org/opencast-ffmpeg-static/ffmpeg-${FFMPEG_VERSION}-${TARGETARCH}-static.tar.xz" \
     | tar xJf - --strip-components 1 --wildcards '*/ffmpeg' '*/ffprobe' \
 && chown root:root ff* \
 && mv ff* /usr/local/bin


FROM scratch AS assembly
COPY --from=build         /                   /
COPY --from=build-ffmpeg  /usr/local/bin/ff*  /usr/local/bin/

COPY etc/pyca.conf etc/gunicorn.conf.py /etc/pyca/
RUN echo 'bind = "0.0.0.0:8000"' >> /etc/pyca/gunicorn.conf.py

RUN addgroup -S -g 800 pyca \
 && adduser -S -D -h /var/lib/pyca -G pyca -u 800 pyca \
 && addgroup pyca audio \
 && addgroup pyca video


FROM scratch AS squash
LABEL org.opencontainers.image.base.name="docker.io/library/alpine:3.19"

COPY --from=assembly / /
WORKDIR /var/lib/pyca

ARG VERSION=main
ARG BUILD_DATE=unknown
ARG GIT_COMMIT=unknown

LABEL maintainer="pyCA team" \
      org.opencontainers.image.title="pyCA" \
      org.opencontainers.image.description="Python Capture Agent for Opencast" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.vendor="Opencast" \
      org.opencontainers.image.authors="pyCA team" \
      org.opencontainers.image.licenses="LGPL-3.0-only" \
      org.opencontainers.image.url="https://github.com/opencast/pyCA/blob/${VERSION}/README.rst" \
      org.opencontainers.image.documentation="https://github.com/opencast/pyCA/blob/${VERSION}/README.rst" \
      org.opencontainers.image.source="https://github.com/opencast/pyCA" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${GIT_COMMIT}"

USER pyca
VOLUME [ "/var/lib/pyca" ]
EXPOSE 8000

ENTRYPOINT [ "pyca" ]
