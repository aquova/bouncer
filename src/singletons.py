from typing import cast, Final

import discord

from config import LOG_CHAN, MAILBOX, SPAM_CHAN, SYS_LOG, WATCHLIST_CHAN
from activity import Syslog
from blocks import BlockedUsers
from spam import Spammers
from waiting import AnsweringMachine
from watcher import Watcher

class Singletons():
    def __init__(self):
        self.am: Final = AnsweringMachine()
        self.blocks: Final = BlockedUsers()
        self.spammers: Final = Spammers()
        self.syslog: Final = Syslog()
        self.watch: Final = Watcher()

        self.mailbox: discord.TextChannel | None = None
        self.log: discord.TextChannel | None = None
        self.spam: discord.TextChannel | None = None
        self.watchlist: discord.TextChannel | None = None

    async def set_channels(self, client: discord.Client):
        self.mailbox = cast(discord.TextChannel, client.get_channel(MAILBOX))
        self.log = cast(discord.TextChannel, client.get_channel(LOG_CHAN))
        self.spam = cast(discord.TextChannel, client.get_channel(SPAM_CHAN))
        self.watchlist = cast(discord.TextChannel, client.get_channel(WATCHLIST_CHAN))
        self.syslog.setup(cast(discord.TextChannel, client.get_channel(SYS_LOG)))

singletons = Singletons()
