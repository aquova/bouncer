import base64, lzma
from datetime import datetime

import discord

from config import PASTE_URL

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

# Creates a URL to be decoded by the web-hosted paste service
# See https://github.com/topaz/paste
def create_paste_link(message: str) -> str:
    # Note that this filters out non-ASCII characters, like emoji, which could potentially be an issue
    # There's no reason why this shouldn't work, except the JS implementation of LZMA/Base64 on the server side
    # doesn't seem to decode it in the same way as Python encodes it, leading to a jumbled mess
    data = message.encode('ascii', errors='ignore')
    compressed = lzma.compress(data, format=lzma.FORMAT_ALONE)
    b64 = base64.b64encode(compressed)
    return f"{PASTE_URL}#{b64.decode()}"

# Sends a Discord message if one will fit into a single post, otherwise encode and link to web
async def send_message(message: str, channel: discord.TextChannel | discord.Thread) -> discord.Message:
    if len(message) > CHAR_LIMIT:
        url = create_paste_link(message)
        mid = await channel.send(f"The reply won't fit into a Discord message, [click here to view]({url}). Also consider shorting the response to this command.")
    else:
        mid = await channel.send(message)
    return mid
