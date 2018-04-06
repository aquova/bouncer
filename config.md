# Bouncer configuration

Included in the repo is a `config_example.json` file, which is read in by the server and used for settings. The various parameters should all be filled in (in quotes), and renamed to `config.json` for the bot to use. The various parameters are:

- discord: Discord secret key
- channels
    - listening: Channel IDs that the bot will accept commands in, should be in quotes and listed inside of `[]`
    - log: Channel ID where the bot will log user infractions
- ageWarning
    - threshold: Age in hours that if any younger with an account younger joins, a message will be sent. Can be left blank to disable
    - channel: The channel ID to send age warnings
- roles: Discord role IDs that the bot will listen to. Can be left blank to enable all roles
- DM
    - ban: When `True`, the bot will send a DM to the specified user when they have been logged as banned via `!ban`
    - warn: When `True`, the bot will send a DM to the specified user when they have been logged as warned via `!warn`
