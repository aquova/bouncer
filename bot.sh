#!/bin/sh

while :
do
    if ! pgrep -x "bouncer.py" > /dev/null
    then
        python3 bouncer.py
    fi
done
