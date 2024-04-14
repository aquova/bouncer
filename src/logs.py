from datetime import datetime, timezone

import discord

import db
import visualize
from client import client
from config import BAN_APPEAL_URL, DM_BAN, DM_WARN, INFO_CHANS, SERVER_NAME
from logtypes import LogTypes, past_tense
from reply import add_context_to_reply_thread
import utils

# Add extra message if more than threshold number of warns
_WARN_THRESHOLD = 3

BAN_KICK_MES = "Hi there! You've been {type} from the {name} Discord for violating the rules: `{mes}`. If you have any questions, and for information on appeals, you can join <{url}>."
SCAM_MES = "Hi there! You've been banned from the {name} Discord for posting scam links. If your account was compromised, please change your password, enable 2FA, and join <{url}> to appeal."
WARN_MES = "Hi there! You've received warning #{count} in the {name} Discord for violating the rules: `{mes}`. Please review {chans} for more info. If you have any questions, you can reply directly to this message to contact the staff."

"""
Search logs

Searches the database for the specified user
"""
def search_logs(user: discord.User) -> str:
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
async def log_user(user: discord.User, reason: str, state: LogTypes, author: discord.User | discord.Member, channel_id: int) -> str:
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
    await add_context_to_reply_thread(channel_id, user, f"`{str(user)}` was {past_tense(state)}", reason)

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
            if state == LogTypes.BAN and DM_BAN:
                await dm_chan.send(BAN_KICK_MES.format(name=SERVER_NAME, type="banned", mes=reason, url=BAN_APPEAL_URL))
            elif state == LogTypes.WARN and DM_WARN:
                info = " and ".join([f"<#{x}>" for x in INFO_CHANS])
                await dm_chan.send(WARN_MES.format(name=SERVER_NAME, count=count, mes=reason, chans=info))
            elif state == LogTypes.KICK and DM_BAN:
                await dm_chan.send(BAN_KICK_MES.format(name=SERVER_NAME, type="kicked", mes=reason, url=BAN_APPEAL_URL))
            elif state == LogTypes.SCAM and DM_BAN:
                await dm_chan.send(SCAM_MES.format(name=SERVER_NAME, url=BAN_APPEAL_URL))
        # Exception handling
        except discord.errors.HTTPException as err:
            if err.code == 50007:
                output += "\nCannot send messages to this user. It is likely that we do not share a server or that they are not accepting my DMs."
            else:
                output += f"\nERROR: While attempting to DM, there was an unexpected error: {err}"

    # Update database
    new_log.message_id = log_mes_id
    db.add_log(new_log)
    return output

"""
Preview message

Prints out Bouncer's DM message as the user will receive it
"""
def preview(reason: str, log_type: LogTypes) -> str:
    if not DM_BAN and (log_type == LogTypes.BAN or log_type == LogTypes.KICK or log_type == LogTypes.SCAM):
        return "DMing the user about their bans is currently off, they won't see any message"

    if not DM_WARN and log_type == LogTypes.WARN:
        return "DMing the user about their warns is currently off, they won't see any message"

    match log_type:
        case LogTypes.BAN:
            return BAN_KICK_MES.format(name=SERVER_NAME, type="banned", mes=reason, url=BAN_APPEAL_URL)
        case LogTypes.WARN:
                info = " and ".join([f"<#{x}>" for x in INFO_CHANS])
                return WARN_MES.format(name=SERVER_NAME, count="X",mes=reason, chans=info)
        case LogTypes.KICK:
                return BAN_KICK_MES.format(name=SERVER_NAME, type="kicked", mes=reason, url=BAN_APPEAL_URL)
        case LogTypes.SCAM:
            return SCAM_MES.format(name=SERVER_NAME, url=BAN_APPEAL_URL)
        case _:
            return "We don't DM the user for those."

"""
Edit log

Edits the specified log index for the user
"""
def edit_log(user: discord.User, index: int, message: str, author: discord.User | discord.Member) -> str:
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
async def remove_error(user: discord.User, index: int) -> str:
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
