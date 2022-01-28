FROM aquova/commonbot:1.7.3.2

RUN apk update && apk add \
    freetype-dev

ADD requirements.txt /bouncer/requirements.txt
RUN pip3 install -r /bouncer/requirements.txt

CMD ["python3", "-u", "/bouncer/main.py"]
