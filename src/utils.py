from datetime import datetime
from textwrap import wrap

import discord

from config import ADMIN_CATEGORIES

CHAR_LIMIT = 1990 # The actual limit is 2000, but we'll be conservative

# Output is of the form YYYY-MM-DD
def format_time(time: datetime) -> str:
    date = str(time).split()[0]
    return date

# Gets the days, hours, minutes, seconds from the delta of two times
def get_time_delta(time1: datetime, time2: datetime) -> tuple[int, int, int, int]:
    # t1 should be larger than t2
    delta = time1 - time2
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return delta.days, hours, minutes, seconds

# Checks if given user has one of the roles specified in config.json
def check_roles(user: discord.Member | discord.User, valid_roles: list[int]) -> bool:
    if isinstance(user, discord.User):
        return False
    for role in valid_roles:
        if user.get_role(role):
            return True
    return False

# Combines message content, attachment URLs, and stickers together
def combine_message(mes: discord.Message) -> str:
    out = mes.content
    for item in mes.attachments:
        out += '\n' + item.url

    for sticker in mes.stickers:
        out += '\n' + sticker.url

    return out

# Interaction wrapper that prevents users from leaking info
async def interaction_response_helper(interaction: discord.Interaction, response: str):
    send_method = interaction.followup.send if interaction.response.is_done() else interaction.response.send_message
    if interaction.channel.category.id in ADMIN_CATEGORIES:
        if len(response) > CHAR_LIMIT:
            messages = split_message(response)
            await send_method(messages[0])
            for m in messages[1:]:
                await interaction.followup.send(m)
        else:
            await send_method(response)
    else:
        await send_method("Don't leak info!", ephemeral=True)

def split_message(message: str) -> list[str]:
    messages = message.split('\n')
    to_send = [messages[0]]
    for msg in messages[1:]:
        if len(msg) >= CHAR_LIMIT:
            to_send += wrap(msg, width=CHAR_LIMIT)
        elif len(msg) + len(to_send[-1]) < CHAR_LIMIT:
            to_send[-1] += f"\n{msg}"
        else:
            to_send.append(msg)
    return to_send

async def send_message(message: str, channel: discord.TextChannel | discord.Thread) -> discord.Message | None:
    messages = split_message(message)
    first_id = None
    for msg in messages:
        if len(msg) > 0:
            try:
                mid = await channel.send(msg)
                first_id = mid if first_id is None else first_id
            except discord.errors.DiscordServerError:
                print("Discord server error, unable to post message")
                break
    return first_id
