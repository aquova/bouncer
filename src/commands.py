import discord, datetime
import config, db, utils
from blocks import BlockedUsers
from config import LogTypes
from waiting import AnsweringMachine
from user import UserLookup

ul = UserLookup()
bu = BlockedUsers()
am = AnsweringMachine()

async def send_help_mes(m, _):
    dmWarns = "On" if config.DM_WARN else "Off"
    dmBans = "On" if config.DM_BAN else "Off"
    helpMes = (
        "Issue a warning: `$warn USER message`\n"
        "Log a ban: `$ban USER reason`\n"
        "Log an unbanning: `$unban USER reason`\n"
        "Log a kick: `$kick USER reason`\n"
        "Search for a user: `$search USER`\n"
        "Create a note about a user: `$note USER message`\n"
        "Remove a user's log: `$remove USER index(optional)`\n"
        "Edit a user's note: `$edit USER index(optional) new_message`\n"
        "View users waiting for a reply: `$waiting`. Clear the list with `$clear`\n"
        "Stop a user from sending DMs to us: `$block/$unblock USERID`\n"
        "Reply to a user in DMs: `$reply USERID` - To reply to the most recent DM: `$reply ^`\n"
        "Plot warn/ban stats: `$graph`\n"
        "View bot uptime: `$uptime`\n"
        "DMing users when they are banned is `{}`\n"
        "DMing users when they are warned is `{}`".format(dmBans, dmWarns)
    )

    await m.channel.send(helpMes)

"""
User Search

Searches the database for the specified user, given a message

Input:
    m: Discord message object
"""
async def userSearch(m, _):
    userid = ul.parse_mention(m)
    if userid == None:
        await m.channel.send("I wasn't able to find a user anywhere based on that message. `$search USER`")
        return

    # Get database values for given user
    search_results = db.search(userid)
    username = ul.fetch_username(m.guild, userid)

    if search_results == []:
        if username != None:
            await m.channel.send("User {} was not found in the database\n".format(username))
        else:
            await m.channel.send("That user was not found in the database or the server\n")
        return

    # Format output message
    out = "User {} was found with the following infractions\n".format(username)
    for index, item in enumerate(search_results):
        # Enumerate each item
        n = "{}. ".format(index + 1)
        n += str(item)

        # If message becomes too long, send what we have and start a new post
        if len(out) + len(n) < config.CHAR_LIMIT:
            out += n
        else:
            await m.channel.send(out)
            out = n

    await m.channel.send(out)

"""
Log User

Notes an infraction for a user

Inputs:
    m: Discord message object
    state: Type of infraction
"""
async def logUser(m, state):
    # Attempt to generate user object
    userid = ul.parse_mention(m)
    if userid == None:
        if state == LogTypes.NOTE:
            await m.channel.send("I wasn't able to understand that message: `$note USER`")
        else:
            await m.channel.send("I wasn't able to understand that message: `$log USER`")
        return

    # Calculate value for 'num' category in database
    # For warns, it's the newest number of warns, otherwise it's a special value
    if state == LogTypes.WARN:
        count = db.get_warn_count(userid)
    else:
        count = state.value
    currentTime = datetime.datetime.utcnow()

    # Attempt to fetch the username for the user
    username = ul.fetch_username(m.guild, userid)
    if username == None:
        username = "ID: " + str(userid)
        await m.channel.send("I wasn't able to find a username for that user, but whatever, I'll do it anyway.")

    # Generate log message, adding URLs of any attachments
    content = utils.combineMessage(m)
    mes = utils.parseMessage(content, username)

    # If they didn't give a message, abort
    if mes == "":
        await m.channel.send("Please give a reason for why you want to log them.")
        return

    # Update records for graphing
    import visualize
    if state == LogTypes.BAN:
        visualize.updateCache(m.author.name, (1, 0), utils.formatTime(currentTime))
    elif state == LogTypes.WARN:
        visualize.updateCache(m.author.name, (0, 1), utils.formatTime(currentTime))
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
        await m.channel.send("This user has received {} warnings or more. It is recommended that they be banned.".format(config.WARN_THRESHOLD))

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
            u = ul.fetch_user(m.guild, userid)
            if u != None:
                DMchan = u.dm_channel
                # If first time DMing, need to create channel
                if DMchan == None:
                    DMchan = await u.create_dm()

                # Only send DM when specified in configs
                if state == LogTypes.BAN and config.DM_BAN:
                    await DMchan.send("Hi there! You've been banned from the Stardew Valley Discord for violating the rules: `{}`. If you have any questions, you can send a message to the moderators via the sidebar at <https://www.reddit.com/r/StardewValley>, and they'll forward it to us.".format(mes))
                elif state == LogTypes.WARN and config.DM_WARN:
                    await DMchan.send("Hi there! You received warning #{} in the Stardew Valley Discord for violating the rules: `{}`. Please review <#445729591533764620> and <#445729663885639680> for more info. If you have any questions, you can reply directly to this message to contact the staff.".format(count, mes))
                elif state == LogTypes.KICK and config.DM_BAN:
                    await DMchan.send("Hi there! You've been kicked from the Stardew Valley Discord for violating the following reason: `{}`. If you have any questions, you can send a message to the moderators via the sidebar at <https://www.reddit.com/r/StardewValley>, and they'll forward it to us.".format(mes))

        # Exception handling
        except discord.errors.HTTPException as e:
            await m.channel.send("ERROR: While attempting to DM, there was an unexpected error. Tell aquova this: {}".format(e))
        except Exception as e:
            await m.channel.send( "ERROR: An unexpected error has occurred. Tell aquova this: {}".format(e))

    # Update database
    new_log.message_url = logMesID
    db.add_log(new_log)

"""
Remove Error

Removes last database entry for specified user

Input:
    m: Discord message object
    edit: Boolean, signifies if this is a deletion (false) or an edit (true)
"""
async def removeError(m, edit):
    userid = ul.parse_mention(m)
    if userid == None:
        if edit:
            await m.channel.send("I wasn't able to understand that message: `$remove USER [num] new_message`")
        else:
            await m.channel.send("I wasn't able to understand that message: `$remove USER [num]`")
        return

    username = ul.fetch_username(m.guild, userid)
    if username == None:
        username = str(userid)

    # If editing, and no message specified, abort.
    mes = utils.parseMessage(m.content, username)
    if mes == "":
        if edit:
            await m.channel.send("You need to specify an edit message")
            return
        else:
            mes = "0"

    try:
        index = int(mes.split()[0]) - 1
        mes = utils.strip(mes)
    except (IndexError, ValueError):
        index = -1

    # Find most recent entry in database for specified user
    search_results = db.search(userid)
    # If no results in database found, can't modify
    if search_results == []:
        await m.channel.send("I couldn't find that user in the database")
    # If invalid index given, yell
    elif (index > len(search_results) - 1) or index < -1:
        await m.channel.send("I can't modify item number {}, there aren't that many for this user".format(index + 1))
    else:
        item = search_results[index]
        import visualize
        if edit:
            if item.log_type == LogTypes.NOTE.value:
                currentTime = datetime.datetime.utcnow()
                item.timestamp = currentTime
                item.log_message = mes
                item.staff = m.author.name
                db.add_log(item)
                out = "The log now reads as follows:\n{}\n".format(str(item))
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
            visualize.updateCache(item.staff, (-1, 0), utils.formatTime(item.timestamp))
        elif item.log_type == LogTypes.WARN:
            visualize.updateCache(item.staff, (0, -1), utils.formatTime(item.timestamp))
        await m.channel.send(out)

        # Search logging channel for matching post, and remove it
        try:
            if item.message_url != 0:
                chan = discord.utils.get(m.guild.channels, id=config.LOG_CHAN)
                m = await chan.fetch_message(item.message_url)
                await m.delete()
        # Print message if unable to find message to delete, but don't stop
        except discord.errors.HTTPException as e:
            print("Unable to find message to delete: {}", str(e))

"""
Block User

Prevents DMs from a given user from being forwarded

Input:
    m: Discord message object
    block: Boolean, true for block, false for unblock
"""
async def blockUser(m, block):
    userid = ul.parse_mention(m)
    if userid == None:
        if block:
            await m.channel.send("I wasn't able to understand that message: `$block USER`")
        else:
            await m.channel.send("I wasn't able to understand that message: `$unblock USER`")
        return

    username = ul.fetch_username(m.guild, userid)
    if username == None:
        username = str(userid)

    # Store in the database that the given user is un/blocked
    # Also update current block list to match
    if block:
        if bu.is_in_blocklist(userid):
            await m.channel.send("Um... That user was already blocked...")
        else:
            bu.block_user(userid)
            await m.channel.send("I have now blocked {}. Their messages will no longer display in chat, but they will be logged for later review.".format(username))
    else:
        if not bu.is_in_blocklist(userid):
            await m.channel.send("That user hasn't been blocked...")
        else:
            bu.unblock_user(userid)
            await m.channel.send("I have now unblocked {}. You will once again be able to hear their dumb bullshit in chat.".format(username))

"""
Reply

Sends a private message to the specified user

Input:
    m: Discord message object
"""
async def reply(m, _):
    # If given '^' instead of user, message the last person to DM bouncer
    # Uses whoever DMed last since last startup, don't bother keeping in database or anything like that
    if m.content.split()[1] == "^":
        if am.recent_reply_exists():
            u = am.get_recent_reply()
        else:
            await m.channel.send("Sorry, I have no previous user stored. Gotta do it the old fashioned way.")
            return
    else:
        # Otherwise, attempt to get object for the specified user
        userid = ul.parse_mention(m)
        if userid == None:
            await m.channel.send("I wasn't able to understand that message: `$reply USER`")
            return

        u = ul.fetch_user(m.guild, userid)
    # If we couldn't find anyone, then they aren't in the server, and can't be DMed
    if u == None:
        await m.channel.send("Sorry, but they need to be in the server for me to message them")
        return
    try:
        content = utils.combineMessage(m)
        mes = utils.removeCommand(content)

        # Don't allow blank messages
        if len(mes) == 0 or mes.isspace():
            await m.channel.send("...That message was blank. Please send an actual message")
            return

        uname = "{}#{}".format(u.name, u.discriminator)
        DMchan = u.dm_channel
        # If first DMing, need to create DM channel
        if DMchan == None:
            DMchan = await u.create_dm()
        # Message sent to user
        await DMchan.send("A message from the SDV staff: {}".format(mes))
        # Notification of sent message to the senders
        await m.channel.send("Message sent to {}.".format(uname))

        # If they were in our answering machine, they have been replied to, and can be removed
        am.remove_entry(u.id)

    # Exception handling
    except discord.errors.HTTPException as e:
        if e.status == 403:
            await m.channel.send("I cannot send messages to this user -- they may have closed DMs, left the server, or blocked me. Or something.")
        else:
            await m.channel.send("ERROR: While attempting to DM, there was an unexpected error. Tell aquova this: {}".format(e))
    except Exception as e:
        await m.channel.send("ERROR: While attempting to DM, there was an unexpected error. Tell aquova this: {}".format(e))
