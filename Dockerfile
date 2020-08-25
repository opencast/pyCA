FROM alpine:3.12 AS build

RUN apk --no-cache add \
      util-linux \
      nodejs npm \
      python3 py3-pip \
      gcc make linux-headers musl-dev python3-dev curl-dev \
 && ln -s /usr/bin/python3 /usr/bin/python

WORKDIR /usr/local/src

COPY requirements.txt package.json package-lock.json ./
RUN pip install -r requirements.txt \
 && npm i

COPY . .
RUN make pypi

FROM alpine:3.12
LABEL maintainer="pyCA team"

COPY --from=build /usr/local/src/dist/pyca-*.tar.gz /tmp/pyca.tar.gz

RUN apk --no-cache --virtual .run-deps add \
      python3 py3-pip \
      ffmpeg \
      libcurl postgresql-libs mariadb-connector-c \
 && apk --no-cache --virtual .build-deps add \
      curl tar xz \
      gcc make linux-headers musl-dev python3-dev curl-dev postgresql-dev mariadb-connector-c-dev \
 && ln -s /usr/bin/python3 /usr/bin/python \
 && pip install \
      /tmp/pyca.tar.gz \
      psycopg2 mysqlclient \
      gunicorn \
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
