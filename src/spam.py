from commonbot.user import UserLookup
import discord
from datetime import datetime
from re import search, IGNORECASE
from config import client, SPAM_CHAN, MUTE_ROLE, CENSOR_SPAM
from commonbot.user import UserLookup, fetch_user

SPAM_MES_THRESHOLD = 3
SPAM_TIME_THRESHOLD = 10 # in secs

ul = UserLookup()

class Spammer:
    def __init__(self, message):
        self.messages = [message]
        self.timestamp = datetime.utcnow()

    def __len__(self):
        return len(self.messages)

    def add(self, message):
        current_time = datetime.utcnow()
        if len(self.messages) > 0 and message.content == self.messages[0].content:
            self.messages.append(message)
            # TODO: May need to update timestamp here, to cover situation where they post slowly then quickly
        else:
            self.messages = [message]
            self.timestamp = current_time

class Spammers:
    def __init__(self):
        self.spammers = {}
        self.notification = None

    def set_channel(self):
        self.notification = client.get_channel(SPAM_CHAN)

    async def check_censor(self, message):
        for item in CENSOR_SPAM:
            if bool(search(item, message.content, IGNORECASE)):
                self.spammers[message.author.id] = Spammer(message)
                await self.mark_spammer(message.author)
                return True
        return False

    async def check_spammer(self, message):
        if message.author.bot or message.content == "":
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

        dt = datetime.utcnow() - self.spammers[uid].timestamp
        if len(self.spammers[uid]) >= SPAM_MES_THRESHOLD and dt.total_seconds() <= SPAM_TIME_THRESHOLD:
            await self.mark_spammer(message.author)
            return True

        return False

    # I'm a little concerned this has the potential for a race condition
    # Need to keep an eye out and see if this is the case
    async def mark_spammer(self, user):
        uid = user.id

        spammer = self.spammers[uid]
        roles = user.roles
        mute_role = discord.utils.get(user.guild.roles, id=MUTE_ROLE)
        if mute_role not in roles:
            roles.append(mute_role)
            await user.edit(roles=roles)

        await self.notification.send(f"<@{uid}> has been spamming the message: `{spammer.messages[0].content}`")

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

            await dm_chan.send(f"Hi there! This is an automated courtesy message informing you that your recent posts have been deleted for spamming. You have been muted from speaking in the server until a moderator can verify your message. If you have any questions, please reply to this bot.")
        except discord.errors.HTTPException as e:
            if e.code != 50007:
                raise discord.errors.HTTPException

    async def unmute(self, message, _):
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

        user_roles = user.roles
        mute_role = discord.utils.get(user.guild.roles, id=MUTE_ROLE)
        if mute_role in user_roles:
            user_roles.remove(mute_role)
            await user.edit(roles=user_roles)
            await message.channel.send(f"<@{uid}> has been unmuted")
        else:
            await message.channel.send(f"<@{uid}> does not appear to have been muted...")
