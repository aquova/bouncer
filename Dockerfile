FROM aquova/discord.py:1.5.1

RUN apk update && apk add \
    freetype-dev

ADD requirements.txt /bouncer/requirements.txt
RUN pip3 install -r /bouncer/requirements.txt
