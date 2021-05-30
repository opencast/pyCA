FROM alpine:3.13 AS build

RUN apk --no-cache add \
      curl-dev \
      g++ \
      gcc \
      linux-headers \
      make \
      musl-dev \
      nodejs \
      npm \
      py3-pip \
      python3 \
      python3-dev \
      util-linux \
 && ln -s /usr/bin/python3 /usr/bin/python

WORKDIR /usr/local/src

COPY requirements.txt package.json package-lock.json ./
RUN pip install -r requirements.txt \
 && npm i

COPY . .
RUN make pypi

FROM alpine:3.13
LABEL maintainer="pyCA team"

ENV FFMPEG_VERSION="20210527041447-N-102608-g7a879cce37"

COPY --from=build /usr/local/src/dist/pyca-*.tar.gz /tmp/pyca.tar.gz

RUN apk --no-cache --virtual .run-deps add \
      libcurl \
      postgresql-libs \
      py3-pip \
      python3 \
 && apk --no-cache --virtual .build-deps add \
      curl \
      curl-dev \
      g++ \
      gcc \
      linux-headers \
      make \
      musl-dev \
      postgresql-dev \
      python3-dev \
      tar \
      xz \
 && ln -s /usr/bin/python3 /usr/bin/python \
 && pip install \
      /tmp/pyca.tar.gz \
      gunicorn \
      psycopg2 \
 && cd /usr/local/bin \
 && curl -sSL "https://s3.opencast.org/opencast-ffmpeg-static/ffmpeg-${FFMPEG_VERSION}.tar.xz" \
     | tar xJf - --strip-components 1 --wildcards '*/ffmpeg' '*/ffprobe' \
 && apk del .build-deps \
 && rm -rf /tmp/pyca.tar.gz

RUN addgroup -S -g 800 pyca \
 && adduser -S -D -h /var/lib/pyca -G pyca -u 800 pyca \
 && addgroup pyca audio \
 && addgroup pyca video

COPY etc/pyca.conf etc/gunicorn.conf.py /etc/pyca/
RUN echo 'bind = "0.0.0.0:8000"' >> /etc/pyca/gunicorn.conf.py

WORKDIR /var/lib/pyca
USER pyca
VOLUME [ "/var/lib/pyca" ]
EXPOSE 8000

ENTRYPOINT [ "pyca" ]
