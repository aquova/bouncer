FROM aquova/commonbot:2.0.0b5

RUN apk update && apk add \
    freetype-dev

ADD requirements.txt /bouncer/requirements.txt
RUN pip3 install -r /bouncer/requirements.txt

CMD ["python3", "-u", "/bouncer/main.py"]
