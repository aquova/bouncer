FROM python:3.11-alpine

RUN apk update && apk add \
    build-base \
    freetype-dev \
    git \
    jpeg-dev

ADD requirements.txt /bouncer/requirements.txt
RUN pip3 install -r /bouncer/requirements.txt

WORKDIR /bouncer
CMD ["git", "submodule", "update", "--init"]
CMD ["python3", "-u", "main.py"]
