#!/bin/sh

while :
do
    if ! pgrep -x "cerberus.py" > /dev/null
    then
        python3 cerberus.py
    fi
done
