from datetime import datetime, timezone

import discord

import config
import db
import visualize
from client import client
from forwarder import message_forwarder
from logtypes import LogTypes
import utils

# Add extra message if more than threshold number of warns
_WARN_THRESHOLD = 3

BAN_KICK_MES = "Hi there! You've been {type} from the Stardew Valley Discord for violating the rules: `{mes}`. If you have any questions, and for information on appeals, you can join <https://discord.gg/uz6KPaCPhf>."
SCAM_MES = "Hi there! You've been banned from the Stardew Valley Discord for posting scam links. If your account was compromised, please change your password, enable 2FA, and join <https://discord.gg/uz6KPaCPhf> to appeal."
WARN_MES = "Hi there! You've received warning #{count} in the Stardew Valley Discord for violating the rules: `{mes}`. Please review <#980331408658661426> and <#980331531425959996> for more info. If you have any questions, you can reply directly to this message to contact the staff."

"""
Search logs

Searches the database for the specified user
"""
def search_logs(user: discord.Member) -> str:
    search_results = db.search(user.id)
    if len(search_results) == 0:
        return f"User {str(user)} was not found in the database\n"
    else:
        # Format output message
        out = f"User `{str(user)}` ({user.id}) was found with the following infractions\n"
        warn_cnt = 0
        for index, item in enumerate(search_results):
            if item.log_type == LogTypes.WARN:
                warn_cnt += 1
                out += f"{index + 1}. {db.UserLogEntry.format(item, warn_cnt)}"
            else:
                out += f"{index + 1}. {db.UserLogEntry.format(item, None)}"
        return out

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
            visualize.update_cache(author.name, (1, 0), utils.format_time(current_time))
        case LogTypes.WARN:
            visualize.update_cache(author.name, (0, 1), utils.format_time(current_time))
        case LogTypes.UNBAN:
            output = "Removing all old logs for unbanning"
            db.clear_user_logs(user.id)

    # Generate message for log channel
    new_log = db.UserLogEntry(None, user.id, state, current_time, reason, author.name, None)
    log_message = f"[{utils.format_time(current_time)}] `{str(user)}` - {new_log.log_word()} by {author.name} - {reason}"
    output += log_message

    # Send ban recommendation, if needed
    count = db.get_warn_count(user.id)
    if (state == LogTypes.WARN and count >= _WARN_THRESHOLD):
        output += f"\nThis user has received {_WARN_THRESHOLD} warnings or more. It is recommended that they be banned."

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
Edit log

Edits the specified log index for the user
"""
def edit_log(user: discord.Member, index: int, message: str, author: discord.User | discord.Member) -> str:
    search_results = db.search(user.id)
    # If no results in database found, can't modify
    if not search_results:
        return "I couldn't find that user in the database"
    # If invalid index given, yell
    # 1-indexed for the users
    if index < 1 or index > len(search_results):
        return f"I can't modify item number {index}, there aren't that many for this user"

    item = search_results[index - 1]
    item.timestamp = datetime.now(timezone.utc)
    item.log_message = message
    item.staff = str(author)
    db.add_log(item)
    return f"The log now reads as follows:\n{db.UserLogEntry.format(item)}"

"""
Remove Error

Removes last database entry for specified user
"""
async def remove_error(user: discord.Member, index: int) -> str:
    search_results = db.search(user.id)
    # If no results in database found, can't modify
    if not search_results:
        return "I couldn't find that user in the database"
    # If invalid index given, yell
    # 1-indexed for the users
    if index < 1 or index > len(search_results):
        return f"I can't modify item number {index}, there aren't that many for this user"

    item = search_results[index - 1]
    if item.dbid is not None: # This is for the linter's sake
        db.remove_log(item.dbid)
    out = f"The following log was deleted:\n{db.UserLogEntry.format(item)}"

    if item.log_type == LogTypes.BAN:
        visualize.update_cache(item.staff, (-1, 0), utils.format_time(item.timestamp))
    elif item.log_type == LogTypes.WARN:
        visualize.update_cache(item.staff, (0, -1), utils.format_time(item.timestamp))

    # Search logging channel for matching post, and remove it
    try:
        if item.message_id != 0 and item.message_id is not None:
            old_mes = await client.log.fetch_message(item.message_id)
            await old_mes.delete()
    # If we were unable to find message to delete, that's okay
    except discord.errors.HTTPException:
        pass
    return out

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

