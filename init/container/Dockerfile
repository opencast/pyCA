FROM docker.io/library/alpine:3.12.0
MAINTAINER Lars Kiesow <lkiesow@uos.de>

RUN apk --update add curl-dev gcc libcurl linux-headers musl-dev py3-pip python3 python3-dev postgresql-libs postgresql-dev \
    && pip install gunicorn pyca psycopg2 \
    && apk del curl-dev gcc linux-headers musl-dev python3-dev postgresql-dev \
    && mkdir /etc/pyca

ADD https://raw.githubusercontent.com/opencast/pyCA/master/etc/pyca.conf /etc/pyca/pyca.conf
ADD https://raw.githubusercontent.com/opencast/pyCA/master/etc/gunicorn.conf.py /etc/pyca/gunicorn.conf.py

# commands:
# pyca
# gunicorn pyca.ui:app

EXPOSE 8000

CMD pyca
