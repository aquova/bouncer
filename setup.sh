#!/bin/bash

# Bash script to setup basic configuration for bouncer

# ANSI colors
RED='\033[0;31m'
YELLOW='\033[0;33m'
GREEN='\033[0;32m'
BLUE='\033[0;36m'
NC='\033[0m'

echo -e "${YELLOW}This is a script to quickly install and setup your new Bouncer bot.${NC}";

# This script assumes this is a Debian-based server with apt
if ! [ -x "$(command -v apt)" ]; then
    echo -e "${RED}This script only works on Debian based servers.${NC}";
    exit 1;
fi

# Install packages
echo -e "${BLUE}Installing necessary packages${NC}";
sudo apt update;
sudo apt install python3 python3-pip python3-virtualenv sqlite3;

# Setup Python
echo -e "${BLUE}Setting up Python virtual environment and libaries${NC}";
python3 -m virtualenv --no-site-packages .;
source bin/activate;
python3 -m pip install -r requirements.txt;

# Make default configuration files
echo -e "${BLUE}Generating default configuration files${NC}";
mkdir -p private;
cat << EOF > private/config.json
{
    "discord": "YOUR DISCORD TOKEN HERE",
    "debug": "False",
    "channels": {
        "listening": [<LIST OF ADMIN CHANNEL IDS>],
        "log": <CHANNEL ID TO LOG EVENTS>,
        "syslog": <CHANNEL ID TO LOG WARNS>
    },
    "roles": [<LIST OF ROLE IDS THAT CAN CONTROL BOT>],
    "owner": <OWNER ID>,
    "DM": {
        "ban": "False",
        "warn": "True"
    },
    "gatekeeper": {
        "role": <ROLE ID TO AWARD>,
        "message": <MESSAGE ID TO MONITOR>,
        "emoji": "<EMOJI NAME>"
    },
    "censor": {
        "regex": ["LIST OF BLACKLISTED REGEX"],
        "notify_chan": <CHANNEL ID TO NOTIFY OF CENSOR BREACH"
    },
    "watcher": {
        "report_channel": <CHANNEL ID>
    }
}
EOF

echo -e "${BLUE}"
echo "Setup complete! The bot can be run by running:";
echo -e "${GREEN}"
echo "source bin/activate";
echo "cd src";
echo "python3 main.py";
echo -e "${NC}";
echo "";
echo -e "${BLUE}If you have any questions about bot configuration, please read setup.md${NC}";
