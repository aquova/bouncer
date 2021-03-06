# Bouncer

A Discord moderator bot, designed to be used with the Stardew Valley server

Written by aquova, 2018-2020

https://github.com/aquova/bouncer

https://discord.gg/stardewvalley

## Overview

This bot was originally written to assist with moderation on the SDV Discord server, but it can be easily used on any server that requires more advanced moderation logging.

My personal hosting of the bot will be private, but users are free to host a version of the bot themselves. Over time, the bot has become more and more specific to the SDV server, so this repo is here more as an example rather than a resource to be directly used by others.

## Features

The bot has several moderation features:

- Logging of user warnings
    - Moderators can log user warnings alongside an explanitory message.
    - Warnings are saved both in a Discord channel specified in `config.json`, as well as saved to a local database.
    - In addition to warnings; bans, kicks, and unbannings can all be noted.
- Storing moderation notes
    - Notes about users are stored privately, for moderators to review later
- User searching
    - The database can be searched by user ID, username or by 'ping'. The bot will then post any noted infractions, as well as their timestamp and stored message
- Removal
    - Everybody makes mistakes. Individual user logs can be specified and deleted.
- DM forwarding
    - Private messages sent to the bot will be automatically forwarded to the channel specified in `config.json`.
    - Moderators can also DM a user via the bot, allowing for collaborative viewing of direct messages.
    - DMs from unruly users can be blocked and unblocked as desired.
    - All DMs are also saved to a local .txt file for easy review.
- Answering Machine
    - A list of unreplied users users can be viewed, to avoid accidentally overlooking a message.
    - The list is automatically pruned after the message gets too old, or if they are replied to.
- User DMing
    - Upon being banned, there is the option to DM a user with the ban message. This can be disabled by setting the "DM" field in `config.json` to false.
- Statistics visualization
    - Statistics about moderator activity can be generated, namely how many warns/bans occurred each month, and how many total warns/bans have been created by each moderator.
- System logs
    - The bot will also monitor all channels and post server-wide changes in users.
    - These include nickname changes, joining, leaving, kicked, banned, joining/leaving VC, and logging of all deleted and modified messages.
- Gatekeeping
    - Users will be unable to speak until they react to a specified message with a specified emoji.
- Debugging
    - A bot instance can be specified as a debugging instance.
    - Non-debugging instances will ignore owner commands when debugging enabled, allowing development work while other instances remain live in the server.
- Censor
    - A regex-based blacklist of banned words can be specified in `config.json`.
    - When a user makes a post with a match, the offending message is deleted and moderators are notified of the infraction.
- Watchlist
    - Possibly problematic users can be added to a 'watchlist', where all their messages are posted for easy viewing.
    - Makes it easy to quickly see if a possibly troll is continuing to post, rather than relying on Discord search.

There is also a `$help` command, which will give the syntax for all of the previously listed commands

For better security, the bot only listens in specific channels for commands, and only accepts commands for users with specific roles. These can be specified, along with other parameters, in the `config.json` file, which is not included for obvious security reasons.

If you wish to run the bot yourself, a rough guide on how to do so is located in `setup.md`, and if you are wanting to run the bot on a Debian-based server (or any with apt-get), there is an easy `setup.sh` installation script.
