from datetime import timedelta
from re import search, IGNORECASE
from typing import cast

import discord

from commonbot.user import UserLookup
from commonbot.utils import check_roles

from client import client
from config import SPAM_CHAN, VALID_ROLES, IGNORE_SPAM

from utils import get_userid

SPAM_MES_THRESHOLD = 5
URL_REGEX = r"https?:\/\/.+\..+"
NORMAL_TIMEOUT_MIN = 10
URL_TIMEOUT_MIN = 60

ul = UserLookup()

class Spammer:
    def __init__(self, message: discord.Message):
        self.messages = [message]

    def __len__(self) -> int:
        return len(self.messages)

    def __str__(self) -> str:
        return self.messages[0].content

    def add(self, message: discord.Message):
        if len(self.messages) > 0 and message.content == self.messages[0].content:
            self.messages.append(message)
        else:
            self.messages = [message]

class Spammers:
    def __init__(self):
        self.spammers = {}

    def set_channel(self):
        self.notification = cast(discord.TextChannel, client.get_channel(SPAM_CHAN))

    async def check_spammer(self, message: discord.Message) -> bool:
        if message.author.bot or message.content == "":
            return False

        if message.channel.id in IGNORE_SPAM:
            return False

        if isinstance(message.author, discord.User):
            return False

        # Don't censor admins
        if check_roles(message.author, VALID_ROLES):
            return False

        uid = message.author.id
        if uid not in self.spammers:
            self.spammers[uid] = Spammer(message)
            return False

        self.spammers[uid].add(message)

        if len(self.spammers[uid]) >= SPAM_MES_THRESHOLD:
            url_spam = bool(search(URL_REGEX, str(self.spammers[uid]), IGNORECASE))
            await self.mark_spammer(message.author, url_spam)
            return True

        return False

    async def mark_spammer(self, user: discord.Member, url: bool):
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

        await self.notification.send(f"<@{uid}> has been timed out for {timeout_len} minutes for spamming the message: `{txt}`")

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
                dm_chan = await client.create_dm(user)

            await dm_chan.send(f"Hi there! This is an automated courtesy message informing you that your post(s) have been deleted either for spamming or attempting to ping everyone: '{txt}'. You have been temporarily muted from speaking in the server while the staff team reviews your message. If you have any questions, please reply to this bot.")
        except discord.errors.HTTPException as err:
            if err.code == 50007:
                pass

    async def unmute(self, message: discord.Message, _):
        uid, _ = await get_userid(ul, message, "unmute")
        if not uid:
            return

        if not message.guild:
            return

        try:
            user = await message.guild.fetch_member(uid)
        except discord.errors.NotFound:
            await message.channel.send("That user does not appear to be in the server")
            return

        if uid in self.spammers:
            del self.spammers[uid]

        if user.is_timed_out():
            try:
                await user.timeout(None)
                await message.channel.send(f"<@{uid}> has been unmuted")
            except discord.errors.Forbidden:
                pass
        else:
            await message.channel.send(f"<@{uid}> does not appear to have been muted...")
