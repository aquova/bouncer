from datetime import datetime, timezone

import discord

import commonbot.utils
import config
import db
import visualize
from client import client
from commonbot.user import UserLookup
from config import CMD_PREFIX
from forwarder import message_forwarder
from logtypes import LogTypes
from utils import get_userid as utils_get_userid

ul = UserLookup()

BAN_KICK_MES = "Hi there! You've been {type} from the Stardew Valley Discord for violating the rules: `{mes}`. If you have any questions, and for information on appeals, you can join <https://discord.gg/uz6KPaCPhf>."
SCAM_MES = "Hi there! You've been banned from the Stardew Valley Discord for posting scam links. If your account was compromised, please change your password, enable 2FA, and join <https://discord.gg/uz6KPaCPhf> to appeal."
WARN_MES = "Hi there! You've received warning #{count} in the Stardew Valley Discord for violating the rules: `{mes}`. Please review <#980331408658661426> and <#980331531425959996> for more info. If you have any questions, you can reply directly to this message to contact the staff."

async def get_userid(mes: discord.Message, cmd: str, args: str = "") -> tuple[int | None, bool]:
    return await utils_get_userid(ul, mes, cmd, args)

def search_logs(user: discord.Member) -> str:
    search_results = db.search(user.id)
    if len(search_results) == 0:
        return f"User {str(user)} was not found in the database\n"
    else:
        # Format output message
        out = f"User `{str(user)}` (ID: {user.id}) was found with the following infractions\n"
        warn_cnt = 0
        for index, item in enumerate(search_results):
            if item.log_type == LogTypes.WARN:
                warn_cnt += 1
                out += f"{index + 1}. {db.UserLogEntry.format(item, warn_cnt)}"
            else:
                out += f"{index + 1}. {db.UserLogEntry.format(item, None)}"
        return out

"""
Get ID

Sends the ID of the corresponding user DM thread, if it exists.
"""
async def get_id(mes: discord.Message, _):
    uid = message_forwarder.get_userid_for_user_reply_thread(mes)
    if uid is None:
        await mes.channel.send("I can't get the user's ID. Are we in a DM thread?")
    else:
        await mes.channel.send(str(uid))

"""
Log User

Notes an infraction for a user
"""
async def log_user(user: discord.Member, reason: str, state: LogTypes, author: discord.User | discord.Member) -> str:
    current_time = datetime.now(timezone.utc)
    output = ""

    if state == LogTypes.SCAM:
        reason = "Banned for sending scam in chat."

    # Update records for graphing
    match state:
        case LogTypes.BAN | LogTypes.SCAM:
            visualize.update_cache(author.name, (1, 0), commonbot.utils.format_time(current_time))
        case LogTypes.WARN:
            visualize.update_cache(author.name, (0, 1), commonbot.utils.format_time(current_time))
        case LogTypes.UNBAN:
            output = "Removing all old logs for unbanning"
            db.clear_user_logs(user.id)

    # Generate message for log channel
    new_log = db.UserLogEntry(None, user.id, state, current_time, reason, author.name, None)
    log_message = f"[{commonbot.utils.format_time(current_time)}] `{str(user)}` - {new_log.log_word()} by {author.name} - {reason}"
    output += log_message

    # Send ban recommendation, if needed
    count = db.get_warn_count(user.id)
    if (state == LogTypes.WARN and count >= config.WARN_THRESHOLD):
        output += f"\nThis user has received {config.WARN_THRESHOLD} warnings or more. It is recommended that they be banned."

    # Record this action in the user's reply thread
    # TODO
    # await _add_context_to_reply_thread(message, user, f"`{str(user)}` was {past_tense(state)}", reason)

    log_mes_id = 0
    # If we aren't noting, need to also write to log channel
    if state != LogTypes.NOTE:
        # Post to channel, keep track of message ID
        log_mes = await client.log.send(log_message)
        log_mes_id = log_mes.id

        try:
            dm_chan = user.dm_channel
            # If first time DMing, need to create channel
            if not dm_chan:
                dm_chan = await user.create_dm()

            # Only send DM when specified in configs
            if state == LogTypes.BAN and config.DM_BAN:
                await dm_chan.send(BAN_KICK_MES.format(type="banned", mes=reason))
            elif state == LogTypes.WARN and config.DM_WARN:
                await dm_chan.send(WARN_MES.format(count=count, mes=reason))
            elif state == LogTypes.KICK and config.DM_BAN:
                await dm_chan.send(BAN_KICK_MES.format(type="kicked", mes=reason))
            elif state == LogTypes.SCAM and config.DM_BAN:
                await dm_chan.send(SCAM_MES)
        # Exception handling
        except discord.errors.HTTPException as err:
            if err.code == 50007:
                output += "\nCannot send messages to this user. It is likely they have DM closed or I am blocked."
            else:
                output += f"\nERROR: While attempting to DM, there was an unexpected error. Tell aquova this: {err}"

    # Update database
    new_log.message_id = log_mes_id
    db.add_log(new_log)
    return output

"""
Show reply thread

Sends the the reply thread for a user so it's easy for staff to find
"""
async def show_reply_thread(mes: discord.Message, _):
    # Attempt to generate user object
    userid, userid_from_message = await get_userid(mes, "open")
    if not userid:
        return

    user = client.get_user(userid)
    if user is None:
        await mes.channel.send("That isn't a valid user.")
        return

    # Show reply thread if it exists
    reply_thread_id = message_forwarder.get_reply_thread_id_for_user(user)
    if reply_thread_id is None:
        await mes.channel.send(f"User <@{user.id}> does not have a reply thread.")
        return

    await mes.channel.send(f"Reply thread for <@{user.id}>: <#{reply_thread_id}>.")

"""
Preview message

Prints out Bouncer's DM message as the user will receive it
"""
def preview(reason: str, log_type: LogTypes) -> str:
    if not config.DM_BAN and (log_type == LogTypes.BAN or log_type == LogTypes.KICK or log_type == LogTypes.SCAM):
        return "DMing the user about their bans is currently off, they won't see any message"

    if not config.DM_WARN and log_type == LogTypes.WARN:
        return "DMing the user about their warns is currently off, they won't see any message"

    match log_type:
        case LogTypes.BAN:
            return BAN_KICK_MES.format(type="banned", mes=reason)
        case LogTypes.WARN:
                return WARN_MES.format(count="X",mes=reason)
        case LogTypes.KICK:
                return BAN_KICK_MES.format(type="kicked", mes=reason)
        case LogTypes.SCAM:
            return SCAM_MES
        case _:
            return "We don't DM the user for those."

"""
Remove Error

Removes last database entry for specified user
"""
async def remove_error(mes: discord.Message, edit: bool):
    userid, userid_from_message = await get_userid(mes, "edit" if edit else "remove", "[num] new_message" if edit else "[num]")
    if not userid:
        return

    username = ul.fetch_username(client, userid)
    if not username:
        username = str(userid)

    # If editing, and no message specified, abort.
    output = commonbot.utils.parse_message(mes.content, username, userid_from_message)
    if output == "":
        if edit:
            await mes.channel.send("You need to specify an edit message")
            return
        else:
            output = "0"

    try:
        index = int(output.split()[0]) - 1
        output = commonbot.utils.strip_words(output, 1)
    except (IndexError, ValueError):
        index = -1

    # Find most recent entry in database for specified user
    search_results = db.search(userid)
    # If no results in database found, can't modify
    if not search_results:
        await mes.channel.send("I couldn't find that user in the database")
    # If invalid index given, yell
    elif (index > len(search_results) - 1) or index < -1:
        await mes.channel.send(f"I can't modify item number {index + 1}, there aren't that many for this user")
    else:
        item = search_results[index]
        if edit:
            if item.log_type == LogTypes.NOTE:
                item.timestamp = datetime.now(timezone.utc)
                item.log_message = output
                item.staff = mes.author.name
                db.add_log(item)
                out = f"The log now reads as follows:\n{db.UserLogEntry.format(item)}\n"
                await mes.channel.send(out)
            else:
                await mes.channel.send("You can only edit notes for now")
            return

        # Everything after here is deletion
        if item.dbid is not None:
            db.remove_log(item.dbid)
        out = "The following log was deleted:\n"
        out += db.UserLogEntry.format(item)

        if item.log_type == LogTypes.BAN:
            visualize.update_cache(item.staff, (-1, 0), commonbot.utils.format_time(item.timestamp))
        elif item.log_type == LogTypes.WARN:
            visualize.update_cache(item.staff, (0, -1), commonbot.utils.format_time(item.timestamp))
        await mes.channel.send(out)

        # Search logging channel for matching post, and remove it
        try:
            if item.message_id != 0 and item.message_id is not None:
                old_mes = await client.log.fetch_message(item.message_id)
                await old_mes.delete()
        # Print message if unable to find message to delete, but don't stop
        except discord.errors.HTTPException as err:
            print(f"Unable to find message to delete: {str(err)}")

"""
Reply

Sends a private message to the specified user
"""
async def reply(user: discord.Member, message: str) -> str:
    try:
        # If first DMing, need to create DM channel
        dm_chan = user.dm_channel
        if not dm_chan:
            dm_chan = await client.create_dm(user)

        await dm_chan.send(f"A message from the SDV staff: {message}")
        client.am.remove_entry(user.id)

        # Add context in the user's reply thread
        # await _add_context_to_reply_thread(mes, user, f"Message sent to `{str(user)}`", message)
        return f"Message sent to `{str(user)}`."
    except discord.errors.HTTPException as err:
        if err.code == 50007:
            return "Cannot send messages to this user. It is likely they have DM closed or I am blocked."
        else:
            return f"ERROR: While attempting to DM, there was an unexpected error. Tell aquova this: {err}"

"""
_add_context_to_reply_thread

Adds information about a moderation action taken on a specific user to the user's reply thread.

If the moderation action already happened in the user's reply thread, no more context is needed, so this does nothing.

Otherwise, it posts a message in the reply thread with the details of the action and a link to the source message.
"""
async def _add_context_to_reply_thread(mes: discord.Message, user: discord.User | discord.Member, context: str, message: str):
    reply_thread_id = message_forwarder.get_reply_thread_id_for_user(user)
    if mes.channel.id == reply_thread_id:
        return # Already in reply thread, nothing to do

    reply_thread = await message_forwarder.get_or_create_user_reply_thread(user, content=message)

    # Suppress embeds so the jump url doesn't show a useless 'Discord - A New Way to Chat....' embed
    await reply_thread.send(f"{context} ({mes.jump_url}): {message}", suppress_embeds=True)


class GetUserForReplyException(Exception):
    """
    Helper exception to make _get_user_for_reply easier to write.

    By raising this the function can bail out early, so fewer levels of if/else nesting are needed.
    """
    pass


"""
_get_user_for_reply

Gets the user to reply to for a reply command.

Based on the reply command staff wrote, and the channel it was sent in, this figures out who to DM.

Returns a user (or None, if staff mentioned a user not in the server) and the number of words to strip from the reply command.
"""
def _get_user_for_reply(message: discord.Message) -> tuple[discord.User | discord.Member | None, int]:
    # If it's a Discord reply to a Bouncer message, use the mention in the message
    if message.reference:
        user_reply = message.reference.cached_message
        if user_reply:
            if user_reply.author == client.user and len(user_reply.mentions) == 1:
                return user_reply.mentions[0], 1

    # If it's a reply thread, the user the reply thread is for, otherwise None
    thread_user = message_forwarder.get_userid_for_user_reply_thread(message)

    # Replying to a user with '^' is no longer supported, but some people might need a reminder
    if message.content.split()[1] == "^":
        raise GetUserForReplyException("Replying to a user with '^' is no longer supported.")

    # The mentioned user, or None if no user is mentioned
    userid = ul.parse_id(message)

    # We pick the user to reply to based on the following table
    # |                     | User Mention                                                    | No User Mention                |
    # |---------------------|-----------------------------------------------------------------|--------------------------------|
    # | Not In Reply Thread | Use the mentioned user                                          | Error - Unknown who to message |
    # | In Reply Thread     | Error - Users are not supposed to be mentioned in reply threads | Use the reply thread user      |

    if userid:
        if thread_user is None:  # User mentioned, not a thread -> use the mentioned user
            return client.get_user(userid), 2
        else:  # User mentioned, reply thread -> error, users are not supposed to be mentioned in reply threads
            raise GetUserForReplyException(f"In user reply threads, mentioning users is disabled. Use `{CMD_PREFIX}reply MSG` to reply to the user the thread is for (or mention any user outside a thread).")
    else:
        if thread_user is None:  # No user mentioned, not a reply thread -> error, unknown who to message
            raise GetUserForReplyException(f"I wasn't able to understand that message: `{CMD_PREFIX}reply USER`")
        else:  # No user mentioned, reply thread -> use reply thread user
            return client.get_user(thread_user), 1

