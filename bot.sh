#!/bin/sh

# Start Python virtualenv
source bin/activate

while :
do
    if ! pgrep -x "bouncer.py" > /dev/null
    then
        python3 bouncer.py
    fi
done
