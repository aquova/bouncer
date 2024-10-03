FROM ghcr.io/astral-sh/uv:python3.12-alpine

RUN apk update && apk add \
    build-base \
    freetype-dev \
    jpeg-dev

ADD . /bouncer
WORKDIR /bouncer
RUN uv sync --frozen
CMD ["uv", "run", "src/main.py"]
