FROM aquova/commonbot:2.0.0.3

RUN apk update && apk add \
    freetype-dev \
    jpeg-dev

ADD requirements.txt /bouncer/requirements.txt
RUN pip3 install -r /bouncer/requirements.txt

WORKDIR /bouncer
CMD ["python3", "-u", "main.py"]
