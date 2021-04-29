# Run with 'docker run -v $(pwd):/bouncer -it bouncer sh'
FROM aquova/commonbot:1.1.0

RUN apk update && apk add \
    freetype-dev

ADD requirements.txt /bouncer/requirements.txt
RUN pip3 install -r /bouncer/requirements.txt
