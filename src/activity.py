from datetime import timedelta, timezone, datetime, UTC

import discord

from utils import send_message

POST_MAX_QUEUE = 5                      # Max number of posts to queue before sending
POST_MAX_DELTA = timedelta(minutes=5)   # Max amount of time posts should remain in queue

EPOCH = datetime(1970, 1, 1, 0, 0, 0, tzinfo=timezone.utc) # Start of Unix time

class Syslog:
    def __init__(self):
        self.logs: list[str] = []
        self.oldest: datetime | None = None
        self.channel: discord.TextChannel | None = None

    def setup(self, syslog: discord.TextChannel):
        self.channel = syslog

    async def add_log(self, message: str):
        now = datetime.now(UTC)
        unix = int((now - EPOCH).total_seconds())
        log = f"<t:{unix}:f> {message}"
        self.logs.append(log)
        if self.oldest is None:
            self.oldest = now
        if len(self.logs) >= POST_MAX_QUEUE or now - self.oldest > POST_MAX_DELTA:
            # Note that this means we only have the potential to post logs when a loggable event fires
            # Given the activity on the server, this seems likely to occur within the max delta time, but other solutions might be needed
            # This also probably can have a race condition, so watch out for that
            await self._post_logs()

    async def _post_logs(self):
        joined = '\n'.join(self.logs)
        # We'll clear the logs first, to prevent issues where the same message is
        # for some reason unable to be sent over and over
        self.logs.clear()
        self.oldest = None
        if self.channel is not None:
            await send_message(joined, self.channel)
