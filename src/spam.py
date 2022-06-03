import discord
from datetime import timedelta
from re import search, IGNORECASE
from client import client
from config import SPAM_CHAN, CENSOR_SPAM, VALID_ROLES
from commonbot.user import UserLookup
from commonbot.utils import check_roles

SPAM_MES_THRESHOLD = 3
URL_REGEX = "https?:\/\/.+\..+"
TIMEOUT_HRS = 1

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
        self.notification = None

    def set_channel(self):
        self.notification = client.get_channel(SPAM_CHAN)

    async def check_censor(self, message: discord.Message) -> bool:
        for item in CENSOR_SPAM:
            if bool(search(item, message.content, IGNORECASE)):
                self.spammers[message.author.id] = Spammer(message)
                await self.mark_spammer(message.author)
                return True
        return False

    async def check_spammer(self, message: discord.Message) -> bool:
        if message.author.bot or message.content == "":
            return False

        # Don't censor admins
        if check_roles(message.author, VALID_ROLES):
            return False

        censored = await self.check_censor(message)
        if censored:
            return True

        uid = message.author.id
        if uid not in self.spammers:
            self.spammers[uid] = Spammer(message)
            return False
        else:
            self.spammers[uid].add(message)

        if len(self.spammers[uid]) >= SPAM_MES_THRESHOLD and bool(search(URL_REGEX, str(self.spammers[uid]), IGNORECASE)):
            await self.mark_spammer(message.author)
            return True

        return False

    async def mark_spammer(self, user: discord.Member):
        uid = user.id

        spammer = self.spammers[uid]
        txt = str(spammer)
        if not user.is_timed_out():
            try:
                await user.timeout(timedelta(hours=TIMEOUT_HRS))
            # Can't timeout roles higher in hierarchy
            except discord.errors.Forbidden:
                pass

        await self.notification.send(f"<@{uid}> has been timed out for {TIMEOUT_HRS} hours for spamming the message: `{txt}`")

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

            await dm_chan.send(f"Hi there! This is an automated courtesy message informing you that your recent posts have been deleted for spamming '{txt}'. You have been muted from speaking in the server until a moderator can verify your message. If you have any questions, please reply to this bot.")
        except discord.errors.HTTPException as e:
            if e.code != 50007:
                raise discord.errors.HTTPException

    async def unmute(self, message: discord.Message, _):
        uid = ul.parse_id(message)
        if not uid:
            await message.channel.send("I wasn't able to find a user in that message")
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
