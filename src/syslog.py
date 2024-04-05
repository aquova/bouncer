import discord
from discord.ext import commands, tasks

from utils import send_message

POST_INTERVAL = 30 # How long between checking whether to post logs, in seconds

class Syslog(commands.Cog):
    def __init__(self):
        self.logs = []
        self.loaded = False

    def setup(self, syslog: discord.TextChannel):
        self.channel = syslog
        if not self._post_logs.is_running():
            self._post_logs.start()

    def cog_load(self):
        self.loaded = True

    def cog_unload(self):
        self._post_logs.cancel()

    def add_log(self, message: str):
        self.logs.append(message)

    def is_loaded(self) -> bool:
        return self.loaded

    @tasks.loop(seconds=POST_INTERVAL)
    async def _post_logs(self):
        if len(self.logs) == 0:
            return
        joined = '\n'.join(self.logs)
        await send_message(joined, self.channel)
        self.logs.clear()
