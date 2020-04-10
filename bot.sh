#!/bin/sh

# Start Python virtualenv
source bin/activate

while :
do
    if ! pgrep -x "src/bouncer.py" > /dev/null
    then
        python3 src/bouncer.py
    fi
done
