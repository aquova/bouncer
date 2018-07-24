#!/bin/sh

if pgrep -x "./programs/ecco.png" > /dev/null
then
    rm ./programs/ecco.png
fi
git pull
