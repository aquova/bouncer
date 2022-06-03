import discord
from datetime import timedelta
from client import client
from config import MAILBOX, TTL_ROLES
from commonbot.utils import combine_message, check_roles

REACTION_THRESHOLD = 3
REACTION_EMOJI = '❌' # The :x: emoji
TIMEOUT_MIN = 10

async def check_tattletale(reaction: discord.Reaction):
    if reaction.emoji != REACTION_EMOJI or reaction.count < REACTION_THRESHOLD:
        return

    m = reaction.message
    if m.author.bot:
        return

    # If enough users have flagged a message, take the following actions:
    # - Remove the flagged message
    # - Time out the flagged user
    # - Notify staff, both of the offending message as well as who reacted, for potential abuse

    # Limited rollout: Only count reactions by users with certain role
    reactors = [x async for x in reaction.users()]
    num_valid_reactors = len([x for x in reactors if check_roles(x, TTL_ROLES)])
    if num_valid_reactors < REACTION_THRESHOLD:
        return
    reactor_list = "\n".join([str(x) for x in reactors])

    if not m.author.is_timed_out():
        await m.author.timeout(timedelta(minutes=TIMEOUT_MIN))

    try:
        await m.delete()
        msg_txt = combine_message(m)

        staff_chan = client.get_channel(MAILBOX)
        report = f"Users have flagged a message by <@{m.author.id}> in <#{m.channel.id}>: {msg_txt}.\n\nThese are the users who flagged:\n {reactor_list}"
        await staff_chan.send(report)
    except discord.NotFound:
        pass
