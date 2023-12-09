from typing import cast

import discord
from discord.ext import commands

from config import CMD_PREFIX, LOG_CHAN, MAILBOX, SYS_LOG, WATCHLIST_CHAN

class DiscordClient(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix=CMD_PREFIX, intents=intents)

    def set_channels(self):
        self.mailbox = cast(discord.TextChannel, self.get_channel(MAILBOX))
        self.log = cast(discord.TextChannel, self.get_channel(LOG_CHAN))
        self.syslog = cast(discord.TextChannel, self.get_channel(SYS_LOG))
        self.watchlist = cast(discord.TextChannel, self.get_channel(WATCHLIST_CHAN))

    async def sync_guild(self, guild: discord.Guild):
        import context
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

client = DiscordClient()
