# Setting up Bouncer for your own use

Bouncer was originally written specifically for the Stardew Valley Discord server, and thus was designed primarily with that server's needs in mind. However, if you wish to host a version yourself, here is how to set up the configuration files to do so.

Keep in mind that since the bot was not designed to be run by others, there are some adjustments that will need to be made. The bot has the phrase "Stardew Valley" hardcoded in several places, such as the DM messages sent to users. The bot may not work properly, or may even crash if you do not have channels set up in the way it expects.

To run the bot, firstly, you must have a configuration file named `config.json` which is structured like so:

```json
{
    "discord":"Bot's Discord Token",
    "server":"Server ID number",
    "channels":{
        "listening":["A list of channel IDs for the bot to listen in, note the [] must be there."],
        "log":"A channel ID for the bot to post logs of warnings/bans/etc",
        "syslog":"A channel ID for the bot to post server changes, such as users joining, leaving, etc."
    },
    "roles":["A list of role IDs that the bot will obey, again the [] must be there."],
    "owner":"The user ID of the owner",
    "DM":{
        "ban":"On", // Whether the bot should send DMs when banning or warning. Should be "On" or "Off"
        "warn":"On" // Don't forget to delete these commends, JSON can't have comments
    },
    "gatekeeper": {
        "role": "Role ID to give",
        "message": "ID of message to watch",
        "emoji": "Emoji reaction to watch for"
    }
}
```

Note that all IDs need to be ints and not strings (unlike older versions of the bot/library).

This file should be kept private, as it contains the bot's user token. It should be placed into a `private` folder, which by default will be ignored by git.

The path to your database should be specifed in `Utils.py` as the `DATABASE_PATH` variable.

Once the file is created, change to the bouncer directory. The necessary Python requirements can then be installed via:

`python3 -m pip install -r requirements.txt`

Finally, the bot can be run via the command:

`./bot.sh`
