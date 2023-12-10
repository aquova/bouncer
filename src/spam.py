from datetime import timedelta, datetime
from re import IGNORECASE, search

import discord

from config import IGNORE_SPAM, VALID_ROLES
from utils import check_roles

SPAM_MES_THRESHOLD = 5
SPAM_TIME_THRESHOLD = timedelta(minutes=10)
URL_REGEX = r"https?:\/\/.+\..+"
NORMAL_TIMEOUT_MIN = 10
URL_TIMEOUT_MIN = 60

class Spammer:
    def __init__(self, message: discord.Message):
        self.reset(message)

    def __len__(self) -> int:
        return len(self.messages)

    def __str__(self) -> str:
        return self.messages[0].content

    def reset(self, message: discord.Message):
        self.messages = [message]
        self.timestamp = datetime.now()

    def add(self, message: discord.Message):
        if len(self.messages) > 0 and message.content == self.messages[0].content:
            self.messages.append(message)
        else:
            self.reset(message)

    def get_timestamp(self) -> datetime:
        return self.timestamp

class Spammers:
    def __init__(self):
        self.spammers = {}

    async def check_spammer(self, message: discord.Message) -> tuple[bool, str]:
        if message.author.bot or message.content == "":
            return (False, "")

        if message.channel.id in IGNORE_SPAM:
            return (False, "")

        if isinstance(message.author, discord.User):
            return (False, "")

        # Don't censor admins
        if check_roles(message.author, VALID_ROLES):
            return (False, "")

        uid = message.author.id
        if uid not in self.spammers:
            self.spammers[uid] = Spammer(message)
            return (False, "")

        self.spammers[uid].add(message)

        if len(self.spammers[uid]) >= SPAM_MES_THRESHOLD and datetime.now() - self.spammers[uid].get_timestamp() < SPAM_TIME_THRESHOLD:
            url_spam = bool(search(URL_REGEX, str(self.spammers[uid]), IGNORECASE))
            response = await self._mark_spammer(message.author, url_spam)
            return (True, response)
        return (False, "")

    async def _mark_spammer(self, user: discord.Member, url: bool) -> str:
        uid = user.id

        spammer = self.spammers[uid]
        timeout_len = NORMAL_TIMEOUT_MIN
        if url:
            timeout_len = URL_TIMEOUT_MIN

        txt = str(spammer)
        if not user.is_timed_out():
            try:
                await user.timeout(timedelta(minutes=timeout_len))
            # Can't timeout roles higher in hierarchy
            except discord.errors.Forbidden:
                pass

        for message in spammer.messages:
            try:
                await message.delete()
            except discord.errors.NotFound:
                pass

        if uid in self.spammers:
            del self.spammers[uid]

        # Create a DM channel between Bouncer if it doesn't exist
        try:
            dm_chan = user.dm_channel
            if not dm_chan:
                dm_chan = await user.create_dm()

            await dm_chan.send(f"Hi there! This is an automated courtesy message informing you that your post(s) have been deleted either for spamming or attempting to ping everyone: '{txt}'. You have been temporarily muted from speaking in the server while the staff team reviews your message. If you have any questions, please reply to this bot.")
        except discord.errors.HTTPException as err:
            if err.code == 50007:
                pass
        return f"<@{uid}> has been timed out for {timeout_len} minutes for spamming the message: `{txt}`"

    """
    Removes any timeout on the specified user
    """
    async def unmute(self, user: discord.Member) -> str:
        if user.id in self.spammers:
            del self.spammers[user.id]

        if user.is_timed_out():
            try:
                await user.timeout(None)
                return f"{str(user)} has been unmuted"
            except discord.errors.Forbidden:
                return "I don't have enough permissions to unmute them"
        else:
            return f"{str(user)} does not appear to have been muted..."
