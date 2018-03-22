# cerberus

A Discord moderator bot, designed to be used with the Stardew Valley server

https://github.com/aquova/cerberus

https://discord.gg/stardewvalley

## Overview

This bot was originally written to assist with moderation on the SDV Discord server, but it can be easily used on any server that requires more advanced moderation logging.

My personal hosting of the bot will be private, but users are free to host a version of the bot themselves.

## Features

The bot has several moderation features:

- Logging of user warnings
    - Moderators can log user warnings with the command `!warned @USERNAME message`, where `@USERNAME` is the mention of the offending user, and `message` are notes to be saved with the warning (such as why they were warned).
    - Warnings are saved both in a channel specified in `config.json`, as well as saved to a local database.
- Logging of user bans
    - Similar to warnings, bans can be logged with `!banned @USERNAME message`
    - Note that users must be pinged for the command to function, so they must be logged before being banned, or else they cannot be pinged.
        - This is likely to change in a later version
- User searching
    - The database can be searched with the command `!search @USERNAME`. The bot will then post any noted infractions, as well as their timestamp and stored message
- Removal
    - Everybody makes mistakes.

## Installation

First install both Python3 and pip, then run the command `pip install -r /path/to/requirements.txt`

Make a file called `config.json`, which contains your Discord bot key, channels IDs for the bot to listen to, a channel ID for the bot to post logs, and any role IDs for the bot to accept commands from. A sample configuration file has been supplied with `config_example.json`.

Once you have added your bot account to your server, the bot can be run by the command `./bot.sh`

