# Run with: docker run -d --restart unless-stopped -v $(pwd):/bouncer bouncer
FROM aquova/commonbot:1.2.0

RUN apk update && apk add \
    freetype-dev

ADD requirements.txt /bouncer/requirements.txt
RUN pip3 install -r /bouncer/requirements.txt

CMD ["python3", "-u", "/bouncer/src/main.py"]
