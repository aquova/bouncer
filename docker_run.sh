#!/bin/bash

DIR=`dirname "$(readlink -f "$0")"`
docker build -t bouncer $DIR
docker run -v $DIR:/bouncer -it bouncer python3 /bouncer/src/main.py
