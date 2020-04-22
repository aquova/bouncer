import discord
from config import CENSOR_LIST, CENSOR_CHAN, SYS_LOG, VALID_INPUT_CHANS
from utils import get_mes_link
from re import search, IGNORECASE

def check_censor(message):
    # If you're posting in an admin channel, you can swear all you like
    if message.channel.id in VALID_INPUT_CHANS:
        return False

    for item in CENSOR_LIST:
        if bool(search(item, message.content, IGNORECASE)):
            return True

    return False

async def censor_message(message):
    # If censor violation found:
    # - Delete message
    # - Post a message removal message ourselves (since bots are normally ignored)
    # - Point the admins to the fact that we deleted a message
    # - DM the user telling them that we deleted their message

    await message.delete()

    censor_mes = "**{}#{}** had a message removed by the censor in <#{}>: `{}`".format(message.author.name, message.author.discriminator, message.channel.id, message.content)
    syslog_chan = discord.utils.get(message.guild.channels, id=SYS_LOG)
    log_message = await syslog_chan.send(censor_mes)

    mod_mes = "Uh oh, looks like the censor might've been tripped.\n{}".format(get_mes_link(log_message))
    chan = discord.utils.get(message.guild.channels, id=CENSOR_CHAN)
    await chan.send(mod_mes)

    # Create a DM channel between Bouncer if it doesn't exist
    dm_chan = message.author.dm_channel
    if dm_chan == None:
        dm_chan = await message.author.create_dm()

    await dm_chan.send("Hi there! This is an automated courtesy message informing you that your post was deleted for containing a censored word: `{}`. This is not a warning. The staff team will examine the context and situation of the censor trip and you will be contacted later only if any disciplinary action is taken.".format(message.content))
