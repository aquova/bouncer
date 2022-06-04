import discord
from datetime import datetime, timezone
import config, db
import commonbot.utils
from client import client
from blocks import BlockedUsers
from config import LogTypes, CMD_PREFIX
from waiting import AnsweringMachine
from commonbot.user import UserLookup

from typing import Optional

ul = UserLookup()
bu = BlockedUsers()
am = AnsweringMachine()

BAN_KICK_MES = "Hi there! You've been {type} from the Stardew Valley Discord for violating the rules: `{mes}`. If you have any questions, and for information on appeals, you can join <https://discord.gg/uz6KPaCPhf>."
SCAM_MES = "Hi there! You've been banned from the Stardew Valley Discord for posting scam links. If your account was compromised, please change your password, enable 2FA, and join <https://discord.gg/uz6KPaCPhf> to appeal."
WARN_MES = "Hi there! You've received warning #{count} in the Stardew Valley Discord for violating the rules: `{mes}`. Please review <#707359005655171172> and <#718593494775496754> for more info. If you have any questions, you can reply directly to this message to contact the staff."

async def send_help_mes(m: discord.Message, _):
    dmWarns = "On" if config.DM_WARN else "Off"
    dmBans = "On" if config.DM_BAN else "Off"
    helpMes = (
        f"Issue a warning: `{CMD_PREFIX}warn <user> <message>`\n"
        f"Log a ban: `{CMD_PREFIX}ban <user> <reason>`\n"
        f"Log an unbanning: `{CMD_PREFIX}unban <user> <reason>`\n"
        f"Log a kick: `{CMD_PREFIX}kick <user> <reason>`\n"
        f"Ban with a pre-made scam message: `{CMD_PREFIX}scam <user>`\n"
        f"Preview what will be sent to the user `{CMD_PREFIX}preview <warn/ban/kick> <reason>`\n"
        "\n"
        f"Search for a user: `{CMD_PREFIX}search <user>`\n"
        f"Create a note about a user: `{CMD_PREFIX}note <user> <message>`\n"
        f"Remove a user's log: `{CMD_PREFIX}remove <user> <index(optional)>`\n"
        f"Edit a user's note: `{CMD_PREFIX}edit <user> <index(optional)> <new_message>`\n"
        "\n"
        f"Reply to a user in DMs: `{CMD_PREFIX}reply <user> <message>`\n"
        f" - To reply to the most recent DM: `{CMD_PREFIX}reply ^ <message>`\n"
        f" - You can also Discord reply to a DM with `{CMD_PREFIX}reply <message>`\n"
        f"View users waiting for a reply: `{CMD_PREFIX}waiting`. Clear the list with `{CMD_PREFIX}clear`\n"
        f"Stop a user from sending DMs to us: `{CMD_PREFIX}block/{CMD_PREFIX}unblock <user>`\n"
        "\n"
        f"Remove a user's 'Muted' role: `{CMD_PREFIX}unmute <user>`\n"
        f"Say a message as the bot: `{CMD_PREFIX}say <channel> <message>`\n"
        "\n"
        f"Watch a user's every move: `{CMD_PREFIX}watch <user>`\n"
        f"Remove user from watch list: `{CMD_PREFIX}unwatch <user>`\n"
        f"List watched users: `{CMD_PREFIX}watchlist`\n"
        "\n"
        f"List what we censor: `{CMD_PREFIX}censor`\n"
        f"Plot warn/ban stats: `{CMD_PREFIX}graph`\n"
        f"View bot uptime: `{CMD_PREFIX}uptime`\n"
        "\n"
        f"DMing users when they are banned is `{dmBans}`\n"
        f"DMing users when they are warned is `{dmWarns}`"
    )

    await m.channel.send(helpMes)

def lookup_username(uid: int) -> Optional[str]:
    username = ul.fetch_username(client, uid)

    if not username:
        check_db =  db.search(uid)
        if check_db != []:
            username = check_db[-1].name
        else:
            return None

    return username

"""
User Search

Searches the database for the specified user, given a message
"""
async def search_command(m: discord.Message, _):
    userid = ul.parse_id(m)
    if not userid:
        await m.channel.send(f"I wasn't able to find a user anywhere based on that message. `{CMD_PREFIX}search USER`")
        return

    output = await search_helper(userid)
    await commonbot.utils.send_message(output, m.channel)

async def search_helper(uid: int) -> str:
    ret = ""
    # Get database values for given user
    search_results = db.search(uid)
    username = lookup_username(uid)

    if search_results == []:
        if username:
            ret += f"User {username} was not found in the database\n"
        else:
            return "That user was not found in the database or the server\n"
    else:
        # Format output message
        out = f"User {username} (ID: {uid}) was found with the following infractions\n"
        for index, item in enumerate(search_results):
            out += f"{index + 1}. {str(item)}"
        ret += out

    censored = db.get_censor_count(uid)
    if not censored:
        ret += "They have never tripped the censor"
    else:
        ret += f"They have tripped the censor {censored[0]} times, most recently on {commonbot.utils.format_time(censored[1])}"

    return ret

"""
Log User

Notes an infraction for a user
"""
async def logUser(m: discord.Message, state: LogTypes):
    # Attempt to generate user object
    userid = ul.parse_id(m)
    if not userid:
        if state == LogTypes.NOTE:
            await m.channel.send(f"I wasn't able to understand that message: `{CMD_PREFIX}note USER`")
        else:
            await m.channel.send(f"I wasn't able to understand that message: `{CMD_PREFIX}log USER`")
        return

    # Calculate value for 'num' category in database
    # For warns, it's the newest number of warns, otherwise it's a special value
    if state == LogTypes.WARN:
        count = db.get_warn_count(userid)
    else:
        count = state.value
    currentTime = datetime.now(timezone.utc)

    # Attempt to fetch the username for the user
    username = lookup_username(userid)
    if not username:
        username = "ID: " + str(userid)
        await m.channel.send("I wasn't able to find a username for that user, but whatever, I'll do it anyway.")

    # Generate log message, adding URLs of any attachments
    content = commonbot.utils.combine_message(m)
    mes = commonbot.utils.parse_message(content, username)

    if state == LogTypes.SCAM:
        mes = "Banned for sending scam in chat."

    # If they didn't give a message, abort
    if mes == "":
        await m.channel.send("Please give a reason for why you want to log them.")
        return

    # Update records for graphing
    import visualize
    if state == LogTypes.BAN or state == LogTypes.SCAM:
        visualize.update_cache(m.author.name, (1, 0), commonbot.utils.format_time(currentTime))
    elif state == LogTypes.WARN:
        visualize.update_cache(m.author.name, (0, 1), commonbot.utils.format_time(currentTime))
    elif state == LogTypes.UNBAN:
        await m.channel.send("Removing all old logs for unbanning")
        db.clear_user_logs(userid)

    # Generate message for log channel
    globalcount = db.get_dbid()
    new_log = db.UserLogEntry(globalcount + 1, userid, username, count, currentTime, mes, m.author.name, None)
    logMessage = str(new_log)
    await m.channel.send(logMessage)

    # Send ban recommendation, if needed
    if (state == LogTypes.WARN and count >= config.WARN_THRESHOLD):
        await m.channel.send(f"This user has received {config.WARN_THRESHOLD} warnings or more. It is recommended that they be banned.")

    logMesID = 0
    # If we aren't noting, need to also write to log channel
    if state != LogTypes.NOTE:
        # Post to channel, keep track of message ID
        try:
            chan = discord.utils.get(m.guild.channels, id=config.LOG_CHAN)
            logMes = await chan.send(logMessage)
            logMesID = logMes.id
        except discord.errors.InvalidArgument:
            await m.channel.send("The logging channel has not been set up in `config.json`. In order to have a visual record, please specify a channel ID.")

        try:
            # Send a DM to the user
            u = client.get_user(userid)
            if u:
                DMchan = u.dm_channel
                # If first time DMing, need to create channel
                if not DMchan:
                    DMchan = await u.create_dm()

                # Only send DM when specified in configs
                if state == LogTypes.BAN and config.DM_BAN:
                    await DMchan.send(BAN_KICK_MES.format(type="banned", mes=mes))
                elif state == LogTypes.WARN and config.DM_WARN:
                    await DMchan.send(WARN_MES.format(count=count, mes=mes))
                elif state == LogTypes.KICK and config.DM_BAN:
                    await DMchan.send(BAN_KICK_MES.format(type="kicked", mes=mes))
                elif state == LogTypes.SCAM and config.DM_BAN:
                    await DMchan.send(SCAM_MES)
        # Exception handling
        except discord.errors.HTTPException as e:
            if e.code == 50007:
                await m.channel.send(f"Cannot send messages to this user. It is likely they have DM closed or I am blocked.")
            else:
                await m.channel.send(f"ERROR: While attempting to DM, there was an unexpected error. Tell aquova this: {e}")
        except Exception as e:
            await m.channel.send(f"ERROR: An unexpected error has occurred. Tell aquova this: {e}")

    # Update database
    new_log.message_id = logMesID
    db.add_log(new_log)

"""
Preview message

Prints out Bouncer's DM message as the user will receive it
"""
async def preview(m: discord.Message, _):
    mes = commonbot.utils.strip_words(m.content, 1)

    state_raw = commonbot.utils.get_first_word(mes)
    mes = commonbot.utils.strip_words(mes, 1)

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
        await m.channel.send(f"I have no idea what a {state_raw} is, but it's certainly not a `ban`, `warn`, or `kick`.")
        return

    # Might as well mimic logging behavior
    if mes == "" and state != LogTypes.SCAM:
        await m.channel.send("Please give a reason for why you want to log them.")
        return

    if state == LogTypes.BAN:
        if config.DM_BAN:
            await m.channel.send(BAN_KICK_MES.format(type="banned", mes=mes))
        else:
            await m.channel.send("DMing the user about their bans is currently off, they won't see any message")
    elif state == LogTypes.WARN:
        if config.DM_WARN:
            await m.channel.send(WARN_MES.format(count="X",mes=mes))
        else:
            await m.channel.send("DMing the user about their warns is currently off, they won't see any message")
    elif state == LogTypes.KICK:
        if config.DM_BAN:
            await m.channel.send(BAN_KICK_MES.format(type="kicked", mes=mes))
        else:
            await m.channel.send("DMing the user about their kicks is currently off, they won't see any message")
    elif state == LogTypes.SCAM:
        if config.DM_BAN:
            await m.channel.send(SCAM_MES)
        else:
            await m.channel.send("DMing the user about their bans is currently off, they won't see any message")

"""
Remove Error

Removes last database entry for specified user
"""
async def removeError(m: discord.Message, edit: bool):
    userid = ul.parse_id(m)
    if not userid:
        if edit:
            await m.channel.send(f"I wasn't able to understand that message: `{CMD_PREFIX}remove USER [num] new_message`")
        else:
            await m.channel.send(f"I wasn't able to understand that message: `{CMD_PREFIX}remove USER [num]`")
        return

    username = lookup_username(userid)
    if not username:
        username = str(userid)

    # If editing, and no message specified, abort.
    mes = commonbot.utils.parse_message(m.content, username)
    if mes == "":
        if edit:
            await m.channel.send("You need to specify an edit message")
            return
        else:
            mes = "0"

    try:
        index = int(mes.split()[0]) - 1
        mes = commonbot.utils.strip_words(mes, 1)
    except (IndexError, ValueError):
        index = -1

    # Find most recent entry in database for specified user
    search_results = db.search(userid)
    # If no results in database found, can't modify
    if search_results == []:
        await m.channel.send("I couldn't find that user in the database")
    # If invalid index given, yell
    elif (index > len(search_results) - 1) or index < -1:
        await m.channel.send(f"I can't modify item number {index + 1}, there aren't that many for this user")
    else:
        item = search_results[index]
        import visualize
        if edit:
            if item.log_type == LogTypes.NOTE.value:
                currentTime = datetime.now(timezone.utc)
                item.timestamp = currentTime
                item.log_message = mes
                item.staff = m.author.name
                db.add_log(item)
                out = f"The log now reads as follows:\n{str(item)}\n"
                await m.channel.send(out)

                return
            else:
                await m.channel.send("You can only edit notes for now")
                return

        # Everything after here is deletion
        db.remove_log(item.dbid)
        out = "The following log was deleted:\n"
        out += str(item)

        if item.log_type == LogTypes.BAN:
            visualize.update_cache(item.staff, (-1, 0), commonbot.utils.format_time(item.timestamp))
        elif item.log_type == LogTypes.WARN:
            visualize.update_cache(item.staff, (0, -1), commonbot.utils.format_time(item.timestamp))
        await m.channel.send(out)

        # Search logging channel for matching post, and remove it
        try:
            if item.message_id != 0:
                chan = discord.utils.get(m.guild.channels, id=config.LOG_CHAN)
                m = await chan.fetch_message(item.message_id)
                await m.delete()
        # Print message if unable to find message to delete, but don't stop
        except discord.errors.HTTPException as e:
            print("Unable to find message to delete: {}", str(e))

"""
Block User

Prevents DMs from a given user from being forwarded
"""
async def blockUser(m: discord.Message, block: bool):
    userid = ul.parse_id(m)
    if not userid:
        if block:
            await m.channel.send(f"I wasn't able to understand that message: `{CMD_PREFIX}block USER`")
        else:
            await m.channel.send(f"I wasn't able to understand that message: `{CMD_PREFIX}unblock USER`")
        return

    username = lookup_username(userid)
    if not username:
        username = str(userid)

    # Store in the database that the given user is un/blocked
    # Also update current block list to match
    if block:
        if bu.is_in_blocklist(userid):
            await m.channel.send("Um... That user was already blocked...")
        else:
            bu.block_user(userid)
            await m.channel.send(f"I have now blocked {username}. Their messages will no longer display in chat, but they will be logged for later review.")
    else:
        if not bu.is_in_blocklist(userid):
            await m.channel.send("That user hasn't been blocked...")
        else:
            bu.unblock_user(userid)
            await m.channel.send(f"I have now unblocked {username}. You will once again be able to hear their dumb bullshit in chat.")

"""
Reply

Sends a private message to the specified user
"""
async def reply(m: discord.Message, _):
    u = None
    metadata_words = 0
    # Check if we are replying via a Discord reply to a Bouncer message
    if m.reference:
        user_reply = m.reference.cached_message
        if user_reply:
            if user_reply.author == client.user and len(user_reply.mentions) == 1:
                u = user_reply.mentions[0]
                metadata_words = 1
    else:
        # If given '^' instead of user, message the last person to DM bouncer
        # Uses whoever DMed last since last startup, don't bother keeping in database or anything like that
        if m.content.split()[1] == "^":
            if am.recent_reply_exists():
                u = am.get_recent_reply()
                metadata_words = 2
            else:
                await m.channel.send("Sorry, I have no previous user stored. Gotta do it the old fashioned way.")
                return
        else:
            # Otherwise, attempt to get object for the specified user
            userid = ul.parse_id(m)
            if not userid:
                await m.channel.send(f"I wasn't able to understand that message: `{CMD_PREFIX}reply USER`")
                return

            u = client.get_user(userid)
            metadata_words = 2

    # If we couldn't find anyone, then they aren't in the server, and can't be DMed
    if not u:
        if m.reference:
            await m.channel.send("Sorry, but I wasn't able to get the user from the message. Odds are the bot was restarted after that was sent. You will need to do it 'the old fashioned way'")
        else:
            await m.channel.send("Sorry, but they need to be in the server for me to message them")
        return
    try:
        content = commonbot.utils.combine_message(m)
        mes = commonbot.utils.strip_words(content, metadata_words)

        # Don't allow blank messages
        if len(mes) == 0 or mes.isspace():
            await m.channel.send("...That message was blank. Please send an actual message")
            return

        DMchan = u.dm_channel
        # If first DMing, need to create DM channel
        if not DMchan:
            DMchan = await u.create_dm()
        # Message sent to user
        await DMchan.send(f"A message from the SDV staff: {mes}")
        # Notification of sent message to the senders
        await m.channel.send(f"Message sent to {str(u)}.")

        # If they were in our answering machine, they have been replied to, and can be removed
        am.remove_entry(u.id)

    # Exception handling
    except discord.errors.HTTPException as e:
        if e.code == 50007:
            await m.channel.send(f"Cannot send messages to this user. It is likely they have DM closed or I am blocked.")
        else:
            await m.channel.send(f"ERROR: While attempting to DM, there was an unexpected error. Tell aquova this: {e}")
    except Exception as e:
        await m.channel.send(f"ERROR: While attempting to DM, there was an unexpected error. Tell aquova this: {e}")

"""
Say

Speaks a message to the specified channel as the bot
"""
async def say(message: discord.Message, _):
    try:
        payload = commonbot.utils.strip_words(message.content, 1)
        channel_id = commonbot.utils.get_first_word(payload)
        channel = discord.utils.get(message.guild.channels, id=int(channel_id))
        m = commonbot.utils.strip_words(payload, 1)
        if m == "" and len(message.attachments) == 0:
            await message.channel.send("You cannot send empty messages.")

        for item in message.attachments:
            f = await item.to_file()
            await channel.send(file=f)

        if m != "":
            await channel.send(m)

        return "Message sent."
    except (IndexError, ValueError):
        await message.channel.send(f"I was unable to find a channel ID in that message. `{CMD_PREFIX}say CHAN_ID message`")
    except AttributeError:
        await message.channel.send("Are you sure that was a channel ID?")
    except discord.errors.HTTPException as e:
        if e.code == 50013:
            await message.channel.send("You do not have permissions to post in that channel.")
        else:
            await message.channel.send(f"Oh god something went wrong, everyone panic! {str(e)}")
