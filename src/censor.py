from re import search, IGNORECASE
import discord
from commonbot.utils import check_roles

import db
from client import client
from config import CENSOR_LIST, CENSOR_SPAM, CENSOR_WATCH, CENSOR_CHAN, SYS_LOG, WATCHLIST_CHAN, VALID_ROLES

async def list_censor(message: discord.Message, _):
    delete_items = '\n'.join(CENSOR_LIST)
    watch_items = '\n'.join(CENSOR_WATCH)
    spam_items = '\n'.join(CENSOR_SPAM)
    mes = f"Here are the things we censor. I hope you know regex.\n\nItems we delete:\n```{delete_items}```\nItems we watch:\n```{watch_items}```\nItems on our spam list:\n```{spam_items}```"

    await message.channel.send(mes)

async def check_censor(message: discord.Message) -> bool:
    # Don't censor admins
    if check_roles(message.author, VALID_ROLES):
        return False

    for item in CENSOR_LIST:
        if bool(search(item, message.content, IGNORECASE)):
            await censor_message(message)
            return True

    for item in CENSOR_WATCH:
        if bool(search(item, message.content, IGNORECASE)):
            await watch_message(message)
            return False

    return False

async def censor_message(message: discord.Message):
    # If censor violation found:
    # - Delete message
    # - Post a message removal message ourselves (since bots are normally ignored)
    # - Point the admins to the fact that we deleted a message
    # - Increment their censor violation in the database
    # - DM the user telling them that we deleted their message

    await message.delete()

    censor_mes = f":face_with_symbols_over_mouth: **{str(message.author)}** (ID: {message.author.id}) had a message removed by the censor in <#{message.channel.id}>: `{message.content}`"
    syslog_chan = discord.utils.get(message.guild.channels, id=SYS_LOG)
    log_message = await syslog_chan.send(censor_mes)

    mod_mes = f"Uh oh, looks like <@{message.author.id}> tripped the censor.\n{log_message.jump_url}"
    chan = discord.utils.get(message.guild.channels, id=CENSOR_CHAN)
    await chan.send(mod_mes)

    db.add_censor_count(message.author.id)

    # Create a DM channel between Bouncer if it doesn't exist
    try:
        dm_chan = message.author.dm_channel
        if not dm_chan:
            dm_chan = await client.create_dm(message.author)

        await dm_chan.send(f"Hi there! This is an automated courtesy message informing you that your post was deleted for containing a censored word: `{message.content}`. This is not a warning. The staff team will examine the context and situation your message, and if any disciplinary action is taken, we will contact you.")
    except discord.errors.HTTPException as e:
        if e.code != 50007:
            raise discord.errors.HTTPException

async def watch_message(message: discord.Message):
    # These are words whose usage we don't want to delete, but we should post to the watch channel
    watch_chan = discord.utils.get(message.guild.channels, id=WATCHLIST_CHAN)
    censor_mes = f"I've flagged a message from **{str(message.author)}** (ID: {message.author.id}) in <#{message.channel.id}>: `{message.content}`\n{message.jump_url}"

    await watch_chan.send(censor_mes)
