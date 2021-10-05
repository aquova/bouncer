import discord, datetime
from datetime import datetime
from re import search, IGNORECASE
from config import client, SPAM_CHAN, MUTE_ROLE, CENSOR_SPAM

SPAM_MES_THRESHOLD = 3
SPAM_TIME_THRESHOLD = 30 # in secs

class Spammer:
    def __init__(self, message):
        self.is_spammer = False
        self.messages = [message]
        self.timestamp = datetime.utcnow()

    def __len__(self):
        return len(self.messages)

    def add(self, message):
        if len(self.messages) > 0 and message.content == self.messages[0].content:
            self.messages.append(message)
        else:
            self.messages = [message]
            self.timestamp = datetime.utcnow()

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
        uid = message.author.id

        if uid not in self.spammers:
            censored = await self.check_censor(message)
            if censored:
                return True
            self.spammers[uid] = Spammer(message)
            return False
        elif self.spammers[uid].is_spammer: # May not be needed as they'll have role
            await message.delete()
            return True
        else:
            censored = await self.check_censor(message)
            if censored:
                return True
            self.spammers[uid].add(message)

        dt = datetime.utcnow() - self.spammers[uid].timestamp
        if len(self.spammers[uid]) >= SPAM_MES_THRESHOLD and dt.total_seconds() <= SPAM_TIME_THRESHOLD:
            await self.mark_spammer(message.author)
            return True

        return False

    async def mark_spammer(self, user):
        uid = user.id
        spammer = self.spammers[uid]
        await self.notification.send(f"{str(user)} ({uid}) has been spamming the message: `{spammer.messages[0].content}`")

        for message in spammer.messages:
            await message.delete()
        spammer.messages = {}

        roles = user.roles
        mute_role = discord.utils.get(user.guild.roles, id=MUTE_ROLE)
        if mute_role not in roles:
            roles.append(mute_role)
            await user.edit(roles=roles)

        # Create a DM channel between Bouncer if it doesn't exist
        dm_chan = user.dm_channel
        if not dm_chan:
            dm_chan = await user.create_dm()

        try:
            await dm_chan.send(f"Hi there! This is an automated courtesy message informing you that your recent posts have been deleted for spamming. You have been muted from speaking in the server until a moderator can verify your message. If you have any questions, please reply to this bot.")
        except discord.errors.HTTPException as e:
            if e.code == 50007:
                pass
            else:
                raise discord.errors.HTTPException