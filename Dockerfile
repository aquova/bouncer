FROM python:alpine

RUN apk update && apk add \
    build-base \
    freetype-dev

ADD requirements.txt /bouncer/requirements.txt
RUN pip3 install -r /bouncer/requirements.txt
