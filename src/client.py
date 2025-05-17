from typing import cast, Final

import discord
from discord.ext import commands

from activity import Syslog
from blocks import BlockedUsers
from config import LOG_CHAN, MAILBOX, SPAM_CHAN, SYS_LOG, WATCHLIST_CHAN
import db
from spam import Spammers
from waiting import AnsweringMachine
from watcher import Watcher

class DiscordClient(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        # The command prefix is never used, but we have to have something
        super().__init__(command_prefix="$", intents=intents)
        db.initialize()

        self.am: Final = AnsweringMachine()
        self.blocks: Final = BlockedUsers()
        self.spammers: Final = Spammers()
        self.syslog: Final = Syslog()
        self.watch: Final = Watcher()

        self.mailbox: discord.TextChannel | None = None
        self.log: discord.TextChannel | None = None
        self.spam: discord.TextChannel | None = None
        self.watchlist: discord.TextChannel | None = None

    async def set_channels(self):
        self.mailbox = cast(discord.TextChannel, self.get_channel(MAILBOX))
        self.log = cast(discord.TextChannel, self.get_channel(LOG_CHAN))
        self.spam = cast(discord.TextChannel, self.get_channel(SPAM_CHAN))
        self.watchlist = cast(discord.TextChannel, self.get_channel(WATCHLIST_CHAN))
        self.syslog.setup(self.get_channel(SYS_LOG))

    async def sync_guild(self, guild: discord.Guild):
        import context
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

client = DiscordClient()
