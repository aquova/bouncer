import discord
from datetime import timedelta
from config import client, MAILBOX
from commonbot.utils import combine_message

REACTION_THRESHOLD = 3
REACTION_EMOJI = '❌' # The :x: emoji
TIMEOUT_MIN = 10

async def check_tattletale(reaction: discord.Reaction, user: discord.Member):
    if reaction.emoji != REACTION_EMOJI or reaction.count < REACTION_THRESHOLD:
        return

    if user.bot:
        return

    # If enough users have flagged a message, take the following actions:
    # - Remove the flagged message
    # - Time out the flagged user
    # - Notify staff, both of the offending message as well as who reacted, for potential abuse

    # If they're timed out, then they've already been taken care of
    # This is to avoid race conditions if several reactions come in quickly
    if reaction.message.author.is_timed_out():
        return

    await reaction.message.author.timeout(timedelta(minutes=TIMEOUT_MIN))
    msg_txt = combine_message(reaction.message)
    reactors = [str(x) async for x in reaction.users()]
    reactor_list = "\n".join(reactors)

    await reaction.message.delete()

    staff_chan = client.get_channel(MAILBOX)
    report = f"Users have flagged a message by <@{reaction.message.author.id}> in <#{reaction.message.channel.id}>: {msg_txt}.\n\nThese are the users who flagged:\n {reactor_list}"
    await staff_chan.send(report)
