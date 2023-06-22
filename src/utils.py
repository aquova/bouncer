import discord

from config import CMD_PREFIX
from forwarder import message_forwarder

from commonbot.user import UserLookup


async def get_userid(ul: UserLookup, mes: discord.Message, cmd: str, args: str = "") -> tuple[int | None, bool]:
    """
    Retrieves the user referenced in the given message.

    Uses an explicit user mention if available, otherwise uses the reply thread user if the command
    is in a reply thread.

    The second return value is useful in case the message needs to be stripped to access the args -
    it indicates how many words to strip:
     - True -> the user came from the message, strip two words (the command, and user reference)
     - False -> the user came from the reply thread, strip one word (the command)

    :param mes: Message to check.
    :param cmd: Command name for help output, if no user is found.
    :param args: Command args for help output, if no user is found.
    :return: The user id (or None if found), and whether the user came from the message (as opposed to from the reply thread).
    """
    # First check message
    userid = ul.parse_id(mes)
    if userid:
        return userid, True

    # If no user in the message, check if it's a reply thread
    thread_user = message_forwarder.get_userid_for_user_reply_thread(mes)
    if thread_user is not None:
        return thread_user, False

    outside_reply_thread = f"{CMD_PREFIX}{cmd} USER {args}".strip()
    inside_reply_thread = f"{CMD_PREFIX}{cmd} {args}".strip()

    # Otherwise send an error
    await mes.channel.send(f"I wasn't able to find a user anywhere based on that message. `{outside_reply_thread}` or `{inside_reply_thread}` in a reply thread")
    return None, False
