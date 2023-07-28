from datetime import datetime, timezone

import discord

import commonbot.utils
from commonbot.user import UserLookup

import config
import db
from blocks import BlockedUsers
from client import client
from config import CMD_PREFIX
from forwarder import message_forwarder
from logtypes import LogTypes, past_tense, present_tense
import visualize
from utils import get_userid as utils_get_userid
from waiting import AnsweringMachine

ul = UserLookup()
bu = BlockedUsers()
am = AnsweringMachine()

BAN_KICK_MES = "Hi there! You've been {type} from the Stardew Valley Discord for violating the rules: `{mes}`. If you have any questions, and for information on appeals, you can join <https://discord.gg/uz6KPaCPhf>."
SCAM_MES = "Hi there! You've been banned from the Stardew Valley Discord for posting scam links. If your account was compromised, please change your password, enable 2FA, and join <https://discord.gg/uz6KPaCPhf> to appeal."
WARN_MES = "Hi there! You've received warning #{count} in the Stardew Valley Discord for violating the rules: `{mes}`. Please review <#980331408658661426> and <#980331531425959996> for more info. If you have any questions, you can reply directly to this message to contact the staff."

async def send_help_mes(mes: discord.Message, _):
    dm_warns = "On" if config.DM_WARN else "Off"
    dm_bans = "On" if config.DM_BAN else "Off"
    help_mes = (
        f"## Logging\n"
        f"Issue a warning: `{CMD_PREFIX}warn <user> <message>`\n"
        f"Log a ban: `{CMD_PREFIX}ban <user> <reason>`\n"
        f"Log an unbanning: `{CMD_PREFIX}unban <user> <reason>`\n"
        f"Log a kick: `{CMD_PREFIX}kick <user> <reason>`\n"
        f"Ban with a pre-made scam message: `{CMD_PREFIX}scam <user>`\n"
        f"Preview what will be sent to the user `{CMD_PREFIX}preview <warn/ban/kick> <reason>`\n"
        f"## Users\n"
        f"Search for a user: `{CMD_PREFIX}search <user>`\n"
        f"Create a note about a user: `{CMD_PREFIX}note <user> <message>`\n"
        f"Remove a user's log: `{CMD_PREFIX}remove <user> <index(optional)>`\n"
        f"Edit a user's note: `{CMD_PREFIX}edit <user> <index(optional)> <new_message>`\n"
        f"## DMs\n"
        f"Reply to a user in DMs: `{CMD_PREFIX}reply <user> <message>`\n"
        f"  You can also Discord reply to a DM with `{CMD_PREFIX}reply <message>`\n"
        f"View users waiting for a reply: `{CMD_PREFIX}waiting`. Clear the list with `{CMD_PREFIX}clear`\n"
        f"Stop a user from sending DMs to us: `{CMD_PREFIX}block/{CMD_PREFIX}unblock <user>`\n"
        f"## Misc\n"
        f"Sync bot commands to the server: `{CMD_PREFIX}sync`\n"
        f"Remove a user's 'Muted' role: `{CMD_PREFIX}unmute <user>`\n"
        f"Say a message as the bot: `{CMD_PREFIX}say <channel> <message>`\n"
        f"## Watchlist\n"
        f"Watch a user's every move: `{CMD_PREFIX}watch <user>`\n"
        f"Remove user from watch list: `{CMD_PREFIX}unwatch <user>`\n"
        f"List watched users: `{CMD_PREFIX}watchlist`\n"
        f"## Stats\n"
        f"Plot warn/ban stats: `{CMD_PREFIX}graph`\n"
        f"View bot uptime: `{CMD_PREFIX}uptime`\n"
        f"## Config\n"
        f"DMing users when they are banned is `{dm_bans}`\n"
        f"DMing users when they are warned is `{dm_warns}`"
    )

    await mes.channel.send(help_mes)

async def clear_am(message: discord.Message, _):
    am.clear_entries()
    await message.channel.send("Cleared waiting messages!")


async def list_waiting(message: discord.Message, _):
    mes_list = am.gen_waiting_list()

    if len(mes_list) == 0:
        await message.channel.send("There are no messages waiting")
    else:
        for mes in mes_list:
            await message.channel.send(mes)


async def sync(message: discord.Message, _):
    if message.guild is not None:
        await client.sync_guild(message.guild)
        await message.channel.send("Server synced")

"""
User Search

Searches the database for the specified user, given a message
"""
async def search_command(mes: discord.Message, _):
    userid, _ = await get_userid(mes, "search")
    if not userid:
        return

    output = await search_helper(userid)
    await commonbot.utils.send_message(output, mes.channel)


async def get_userid(mes: discord.Message, cmd: str, args: str = "") -> tuple[int | None, bool]:
    return await utils_get_userid(ul, mes, cmd, args)


async def search_helper(uid: int) -> str:
    ret = ""
    # Get database values for given user
    search_results = db.search(uid)
    username = ul.fetch_username(client, uid)

    if not search_results:
        if username:
            ret += f"User {username} was not found in the database\n"
        else:
            return "That user was not found in the database or the server\n"
    else:
        # Format output message
        out = f"User `{username}` (ID: {uid}) was found with the following infractions\n"
        warn_cnt = 0
        for index, item in enumerate(search_results):
            if item.log_type == LogTypes.WARN:
                warn_cnt += 1
                out += f"{index + 1}. {db.UserLogEntry.format(item, warn_cnt)}"
            else:
                out += f"{index + 1}. {db.UserLogEntry.format(item, None)}"
        ret += out

    return ret

"""
Log User

Notes an infraction for a user
"""
async def log_user(mes: discord.Message, state: LogTypes):
    # Attempt to generate user object
    userid, userid_from_message = await get_userid(mes, present_tense(state))
    if not userid:
        return

    current_time = datetime.now(timezone.utc)
    # Attempt to fetch the username for the user
    username = ul.fetch_username(client, userid)
    if not username:
        username = "ID: " + str(userid)
        await mes.channel.send("I wasn't able to find a username for that user, but whatever, I'll do it anyway.")

    # Generate log message, adding URLs of any attachments
    content = commonbot.utils.combine_message(mes)
    output = commonbot.utils.parse_message(content, username, userid_from_message)

    if state == LogTypes.SCAM:
        output = "Banned for sending scam in chat."

    # If they didn't give a message, abort
    if output == "":
        await mes.channel.send("Please give a reason for why you want to log them.")
        return

    # Update records for graphing
    match state:
        case LogTypes.BAN | LogTypes.SCAM:
            visualize.update_cache(mes.author.name, (1, 0), commonbot.utils.format_time(current_time))
        case LogTypes.WARN:
            visualize.update_cache(mes.author.name, (0, 1), commonbot.utils.format_time(current_time))
        case LogTypes.UNBAN:
            await mes.channel.send("Removing all old logs for unbanning")
            db.clear_user_logs(userid)

    # Generate message for log channel
    new_log = db.UserLogEntry(None, userid, state, current_time, output, mes.author.name, None)
    log_message = f"[{commonbot.utils.format_time(current_time)}] `{username}` - {new_log.log_word()} by {mes.author.name} - {output}"
    await mes.channel.send(log_message)

    # Send ban recommendation, if needed
    count = db.get_warn_count(userid)
    if (state == LogTypes.WARN and count >= config.WARN_THRESHOLD):
        await mes.channel.send(f"This user has received {config.WARN_THRESHOLD} warnings or more. It is recommended that they be banned.")

    # Record this action in the user's reply thread
    user = client.get_user(userid)
    if user:
        await _add_context_to_reply_thread(mes, user, f"`{str(user)}` was {past_tense(state)}", output)

    log_mes_id = 0
    # If we aren't noting, need to also write to log channel
    if state != LogTypes.NOTE:
        # Post to channel, keep track of message ID
        log_mes = await client.log.send(log_message)
        log_mes_id = log_mes.id

        try:
            # Send a DM to the user
            user = client.get_user(userid)
            if user:
                dm_chan = user.dm_channel
                # If first time DMing, need to create channel
                if not dm_chan:
                    dm_chan = await user.create_dm()

                # Only send DM when specified in configs
                if state == LogTypes.BAN and config.DM_BAN:
                    await dm_chan.send(BAN_KICK_MES.format(type="banned", mes=output))
                elif state == LogTypes.WARN and config.DM_WARN:
                    await dm_chan.send(WARN_MES.format(count=count, mes=output))
                elif state == LogTypes.KICK and config.DM_BAN:
                    await dm_chan.send(BAN_KICK_MES.format(type="kicked", mes=output))
                elif state == LogTypes.SCAM and config.DM_BAN:
                    await dm_chan.send(SCAM_MES)
        # Exception handling
        except discord.errors.HTTPException as err:
            if err.code == 50007:
                await mes.channel.send("Cannot send messages to this user. It is likely they have DM closed or I am blocked.")
            else:
                await mes.channel.send(f"ERROR: While attempting to DM, there was an unexpected error. Tell aquova this: {err}")

    # Update database
    new_log.message_id = log_mes_id
    db.add_log(new_log)

"""
Preview message

Prints out Bouncer's DM message as the user will receive it
"""
async def preview(mes: discord.Message, _):
    output = commonbot.utils.strip_words(mes.content, 1)

    state_raw = commonbot.utils.get_first_word(output)
    output = commonbot.utils.strip_words(output, 1)

    state = None
    if state_raw == "ban":
        state = LogTypes.BAN
    elif state_raw == "kick":
        state = LogTypes.KICK
    elif state_raw == "warn":
        state = LogTypes.WARN
    elif state_raw == "scam":
        state = LogTypes.SCAM
    else:
        await mes.channel.send(f"I have no idea what a {state_raw} is, but it's certainly not a `ban`, `warn`, or `kick`.")
        return

    # Might as well mimic logging behavior
    if output == "" and state != LogTypes.SCAM:
        await mes.channel.send("Please give a reason for why you want to log them.")
        return

    match state:
        case LogTypes.BAN:
            if config.DM_BAN:
                await mes.channel.send(BAN_KICK_MES.format(type="banned", mes=output))
            else:
                await mes.channel.send("DMing the user about their bans is currently off, they won't see any message")
        case LogTypes.WARN:
            if config.DM_WARN:
                await mes.channel.send(WARN_MES.format(count="X",mes=output))
            else:
                await mes.channel.send("DMing the user about their warns is currently off, they won't see any message")
        case LogTypes.KICK:
            if config.DM_BAN:
                await mes.channel.send(BAN_KICK_MES.format(type="kicked", mes=output))
            else:
                await mes.channel.send("DMing the user about their kicks is currently off, they won't see any message")
        case LogTypes.SCAM:
            if config.DM_BAN:
                await mes.channel.send(SCAM_MES)
            else:
                await mes.channel.send("DMing the user about their bans is currently off, they won't see any message")

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
Block User

Prevents DMs from a given user from being forwarded
"""
async def block_user(mes: discord.Message, block: bool):
    userid, _ = await get_userid(mes, "block" if block else "unblock")
    if not userid:
        return

    username = ul.fetch_username(client, userid)
    if not username:
        username = str(userid)

    # Store in the database that the given user is un/blocked
    # Also update current block list to match
    if block:
        if bu.is_in_blocklist(userid):
            await mes.channel.send("Um... That user was already blocked...")
        else:
            bu.block_user(userid)
            await mes.channel.send(f"I have now blocked {username}. Their DMs will no longer be forwarded.")
    else:
        if not bu.is_in_blocklist(userid):
            await mes.channel.send("That user hasn't been blocked...")
        else:
            bu.unblock_user(userid)
            await mes.channel.send(f"I have now unblocked {username}. Their DMs will now be forwarded.")

"""
Reply

Sends a private message to the specified user
"""
async def reply(mes: discord.Message, _):
    try:
        user, metadata_words = _get_user_for_reply(mes)
    except GetUserForReplyException as err:
        await mes.channel.send(str(err))
        return

    # If we couldn't find anyone, then they aren't in the server, and can't be DMed
    if not user:
        if mes.reference:
            await mes.channel.send("Sorry, but I wasn't able to get the user from the message. Odds are the bot was restarted after that was sent. You will need to do it 'the old fashioned way'")
        else:
            await mes.channel.send("Sorry, but they need to be in the server for me to message them")
        return

    try:
        content = commonbot.utils.combine_message(mes)
        output = commonbot.utils.strip_words(content, metadata_words)

        # Don't allow blank messages
        if len(output) == 0 or output.isspace():
            await mes.channel.send("...That message was blank. Please send an actual message")
            return

        dm_chan = user.dm_channel
        # If first DMing, need to create DM channel
        if not dm_chan:
            dm_chan = await client.create_dm(user)
        # Message sent to user
        await dm_chan.send(f"A message from the SDV staff: {output}")
        # Notification of sent message to the senders
        await mes.channel.send(f"Message sent to `{str(user)}`.")

        # If they were in our answering machine, they have been replied to, and can be removed
        am.remove_entry(user.id)

        # Add context in the user's reply thread
        await _add_context_to_reply_thread(mes, user, f"Message sent to `{str(user)}`", output)

    # Exception handling
    except discord.errors.HTTPException as err:
        if err.code == 50007:
            await mes.channel.send("Cannot send messages to this user. It is likely they have DM closed or I am blocked.")
        else:
            await mes.channel.send(f"ERROR: While attempting to DM, there was an unexpected error. Tell aquova this: {err}")


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


"""
Say

Speaks a message to the specified channel as the bot
"""
async def say(message: discord.Message, _):
    try:
        payload = commonbot.utils.strip_words(message.content, 1)
        guild = message.guild
        if guild is None:
            return
        channel_id = commonbot.utils.get_first_word(payload)
        channel = discord.utils.get(guild.channels, id=int(channel_id))
        if channel is None:
            raise AttributeError
        elif isinstance(channel, (discord.ForumChannel, discord.CategoryChannel)):
            return

        output = commonbot.utils.strip_words(payload, 1)
        if output == "" and len(message.attachments) == 0:
            await message.channel.send("You cannot send empty messages.")

        for item in message.attachments:
            file = await item.to_file()
            await channel.send(file=file)

        if output != "":
            await channel.send(output)

        return "Message sent."
    except (IndexError, ValueError):
        await message.channel.send(f"I was unable to find a channel ID in that message. `{CMD_PREFIX}say CHAN_ID message`")
    except AttributeError:
        await message.channel.send("Are you sure that was a channel ID?")
    except discord.errors.HTTPException as err:
        if err.code == 50013:
            await message.channel.send("You do not have permissions to post in that channel.")
        else:
            await message.channel.send(f"Oh god something went wrong, everyone panic! {str(err)}")
