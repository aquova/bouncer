from typing import cast

import discord

from config import LOG_CHAN, MAILBOX, SYS_LOG, WATCHLIST_CHAN


class DiscordClient(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = discord.app_commands.CommandTree(self)

    def set_channels(self):
        self.mailbox = cast(discord.TextChannel, self.get_channel(MAILBOX))
        self.log = cast(discord.TextChannel, self.get_channel(LOG_CHAN))
        self.syslog = cast(discord.TextChannel, self.get_channel(SYS_LOG))
        self.watchlist = cast(discord.TextChannel, self.get_channel(WATCHLIST_CHAN))

    async def sync_guild(self, guild: discord.Guild):
        import context
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

my_intents = discord.Intents.all()
client = DiscordClient(intents=my_intents)
