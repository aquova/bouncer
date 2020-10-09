#!/bin/bash

DIR=`dirname "$(readlink -f "$0")"`
docker build -t aquova/bouncer $DIR
docker run -v $DIR:/bouncer -it aquova/bouncer python3 /bouncer/src/main.py
