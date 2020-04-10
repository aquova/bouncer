# Bouncer
# Written by aquova, 2018-2020
# https://github.com/aquova/bouncer

import discord, datetime, asyncio, os, subprocess, sys
from dataclasses import dataclass
import Utils
import config, db, waiting
from blocks import BlockedUsers
from timekeep import Timekeeper
from user import UserLookup
from config import LogTypes

debugging = False

# Initialize client and helper classes
client = discord.Client()
db.initialize()
ul = UserLookup()
bu = BlockedUsers()
am = waiting.AnsweringMachine()
tk = Timekeeper()

# Constants
# Discord has a 2000 message character limit
CHAR_LIMIT = 2000
# Add extra message if more than threshold number of warns
WARN_THRESHOLD = 3

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
        if len(out) + len(n) < CHAR_LIMIT:
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
    content = Utils.combineMessage(m)
    mes = Utils.parseMessage(content, username)

    # If they didn't give a message, abort
    if mes == "":
        await m.channel.send("Please give a reason for why you want to log them.")
        return

    # Update records for graphing
    import Visualize
    if state == LogTypes.BAN:
        Visualize.updateCache(m.author.name, (1, 0), Utils.formatTime(currentTime))
    elif state == LogTypes.WARN:
        Visualize.updateCache(m.author.name, (0, 1), Utils.formatTime(currentTime))
    elif state == LogTypes.UNBAN:
        # Verify that the user really did mean to unban
        def unban_check(check_mes):
            if check_mes.author == m.author and check_mes.channel == m.channel:
                # The API is stupid, returning a boolean will keep the check open, you have to return something non-false
                if check_mes.content.upper() == 'YES' or check_mes.content.upper() == 'Y':
                    return 'Y'
                else:
                    return 'N'

        # In the event of an unban, we need to first
        # A. Ask if they are sure they meant to do this
        await m.channel.send("In order to log an unban, all old logs will be removed. Are you sure? Y/[N]")
        check = await client.wait_for('message', check=unban_check, timeout=10.0)
        # I have no idea why this returns a message and not just 'Y'
        if check.content.upper() == 'Y':
            # B. If so, clear out all previous logs
            await m.channel.send("Very well, removing all old logs to unban")
            db.clear_user_logs(userid)
        else:
            # Abort if they responded negatively
            await m.channel.send("Unban aborted.")
            return

    # Generate message for log channel
    globalcount = db.get_dbid()
    new_log = db.UserLogEntry(globalcount + 1, userid, username, count, currentTime, mes, m.author.name, None)
    logMessage = str(new_log)
    await m.channel.send(logMessage)

    # Send ban recommendation, if needed
    if (state == LogTypes.WARN and count >= WARN_THRESHOLD):
        await m.channel.send("This user has received {} warnings or more. It is recommended that they be banned.".format(WARN_THRESHOLD))

    logMesID = 0
    # If we aren't noting, need to also write to log channel
    if state != LogTypes.NOTE:
        # Post to channel, keep track of message ID
        try:
            chan = client.get_channel(config.LOG_CHAN)
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
    mes = Utils.parseMessage(m.content, username)
    if mes == "":
        if edit:
            await m.channel.send("You need to specify an edit message")
            return
        else:
            mes = "0"

    try:
        index = int(mes.split()[0]) - 1
        mes = Utils.strip(mes)
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
        import Visualize
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
            Visualize.updateCache(item.staff, (-1, 0), Utils.formatTime(item.timestamp))
        elif item.log_type == LogTypes.WARN:
            Visualize.updateCache(item.staff, (0, -1), Utils.formatTime(item.timestamp))
        await m.channel.send(out)

        # Search logging channel for matching post, and remove it
        try:
            if item.message_url != 0:
                chan = client.get_channel(config.LOG_CHAN)
                m = await chan.fetch_message(item.message_url)
                await m.delete()
        # Print message if unable to find message to delete, but don't stop
        except HTTPException as e:
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
        content = Utils.combineMessage(m)
        mes = Utils.removeCommand(content)

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
        am.remove_entry(userid)

    # Exception handling
    except Exception as e:
        if e.status == 403:
            await m.channel.send("I cannot send messages to this user -- they may have closed DMs, left the server, or blocked me. Or something.")
        else:
            await m.channel.send("ERROR: While attempting to DM, there was an unexpected error. Tell aquova this: {}".format(e))

"""
On Ready

Occurs when Discord bot is first brought online
"""
@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)

    # Load any users who were banned into memory
    bu.populate_blocklist()

    # Text Bouncer's activity status
    activity_object = discord.Activity(name="for your reports!", type=discord.ActivityType.watching)
    await client.change_presence(activity=activity_object)

"""
On Member Update

Occurs when a user updates an attribute (nickname, roles)
"""
@client.event
async def on_member_update(before, after):
    # If debugging, don't process
    if config.DEBUG_BOT:
        return
    # If nickname has changed
    if before.nick != after.nick:
        # If they don't have an ending nickname, they reset to their actual username
        if after.nick == None:
            mes = "**{}#{}** has reset their username".format(after.name, after.discriminator)
        else:
            new = after.nick
            mes = "**{}#{}** is now known as `{}`".format(after.name, after.discriminator, after.nick)
        chan = client.get_channel(config.SYS_LOG)
        await chan.send(mes)
    # If role quantity has changed
    elif before.roles != after.roles:
        # Determine role difference, post about it
        if len(before.roles) > len(after.roles):
            missing = [r for r in before.roles if r not in after.roles]
            mes = "**{}#{}** had the role `{}` removed.".format(after.name, after.discriminator, missing[0])
        else:
            newRoles = [r for r in after.roles if r not in before.roles]
            mes = "**{}#{}** had the role `{}` added.".format(after.name, after.discriminator, newRoles[0])
        chan = client.get_channel(config.SYS_LOG)
        await chan.send(mes)

"""
On Member Ban

Occurs when a user is banned
"""
@client.event
async def on_member_ban(server, member):
    # If debugging, don't process
    if config.DEBUG_BOT:
        return

    # We can remove banned user from our answering machine now
    am.remove_entry(member.id)

    # Keep a record of their banning, in case the log is made after they're no longer here
    username = "{}#{}".format(member.name, member.discriminator)
    ul.add_ban(member.id, username)
    mes = "**{} ({})** has been banned.".format(username, member.id)
    chan = client.get_channel(config.SYS_LOG)
    await chan.send(mes)

"""
On Member Remove

Occurs when a user leaves the server
"""
@client.event
async def on_member_remove(member):
    # If debugging, don't process
    if config.DEBUG_BOT:
        return

    # We can remove left users from our answering machine
    am.remove_entry(member.id)

    # Remember that the user has left, in case we want to log after they're gone
    username = "{}#{}".format(member.name, member.discriminator)
    ul.add_ban(member.id, username)
    mes = "**{}#{} ({})** has left".format(username, member.id)
    chan = client.get_channel(config.SYS_LOG)
    await chan.send(mes)

"""
On Raw Reaction Add

Occurs when a reaction is applied to a message
Needs to be raw reaction so it can still get reactions after reboot
"""
@client.event
async def on_raw_reaction_add(payload):
    # If debugging, don't process
    if config.DEBUG_BOT:
        return
    if payload.message_id == config.GATE_MES and payload.emoji.name == config.GATE_EMOJI:
        # Raw payload just returns IDs, so need to iterate through connected servers to get server object
        # Since each bouncer instance will only be in one server, it should be quick.
        # If bouncer becomes general purpose (god forbid), may need to rethink this
        try:
            server = [x for x in client.guilds if x.id == payload.guild_id][0]
            new_role = discord.utils.get(server.roles, id=config.GATE_ROLE)
            target_user = discord.utils.get(server.members, id=payload.user_id)
            await target_user.add_roles(new_role)
        except IndexError as e:
            print("Something has seriously gone wrong.")
            print("Error: {}".format(e))

"""
On Message Delete

Occurs when a user's message is deleted
"""
@client.event
async def on_message_delete(message):
    # If debugging, don't process
    if config.DEBUG_BOT:
        return
    # Don't process bot accounts
    if message.author.bot:
        return
    mes = "**{}#{}** deleted in <#{}>: `{}`".format(message.author.name, message.author.discriminator, message.channel.id, message.content)
    # Adds URLs for any attachments that were included in deleted message
    # These will likely become invalid, but it's nice to note them anyway
    if message.attachments != []:
        for item in message.attachments:
            # Break into seperate parts if we're going to cross character limit
            if len(mes) + len(item.url) > CHAR_LIMIT:
                await chan.send(mes)
                mes = item.url
            else:
                mes += '\n' + item.url
    chan = client.get_channel(config.SYS_LOG)
    await chan.send(mes)

"""
On Message Edit

Occurs when a user edits a message
"""
@client.event
async def on_message_edit(before, after):
    # If debugging, don't process
    if config.DEBUG_BOT:
        return

    # Don't process bot accounts
    if before.author.bot:
        return

    # Prevent embedding of content from triggering the log
    if before.content == after.content:
        return
    try:
        chan = client.get_channel(config.SYS_LOG)
        mes = "**{}#{}** modified in <#{}>: `{}`".format(before.author.name, before.author.discriminator, before.channel.id, before.content)

        # Break into seperate parts if we're going to cross character limit
        if len(mes) + len(after.content) > (CHAR_LIMIT + 5):
            await chan.send(mes)
            mes = ""

        mes += "to `{}`".format(after.content)
        await chan.send(mes)
    except discord.errors.HTTPException as e:
        print("Unknown error with editing message. This message was unable to post for this reason: {}\n".format(e))

"""
On Member Join

Occurs when a user joins the server
"""
@client.event
async def on_member_join(member):
    # If debugging, don't process
    if config.DEBUG_BOT:
        return
    mes = "**{}#{} ({})** has joined".format(member.name, member.discriminator, member.id)
    chan = client.get_channel(config.SYS_LOG)
    await chan.send(mes)

"""
On Voice State Update

Occurs when a user joins/leaves an audio channel
"""
@client.event
async def on_voice_state_update(member, before, after):
    # If debugging, don't process
    if config.DEBUG_BOT:
        return

    # Don't process bot accounts
    if member.bot:
        return

    if after.channel == None:
        mes = "**{}#{}** has left voice channel {}".format(member.name, member.discriminator, before.channel.name)
        chan = client.get_channel(config.SYS_LOG)
        await chan.send(mes)
    elif before.channel == None:
        mes = "**{}#{}** has joined voice channel {}".format(member.name, member.discriminator, after.channel.name)
        chan = client.get_channel(config.SYS_LOG)
        await chan.send(mes)

FUNC_DICT = {
    "$warn": [logUser, LogTypes.WARN],
    "$ban": [logUser, LogTypes.BAN],
    "$kick": [logUser, LogTypes.KICK],
    "$unban": [logUser, LogTypes.UNBAN],
    "$note": [logUser, LogTypes.NOTE],
    "$search": [userSearch, None],
    "$remove": [removeError, False],
    "$block": [blockUser, True],
    "$unblock": [blockUser, False],
    "$reply": [reply, None],
    "$edit": [removeError, True]
}

"""
On Message

Occurs when a user posts a message
More or less the main function
"""
@client.event
async def on_message(message):
    global debugging

    # Bouncer should not react to its own messages
    if message.author.id == client.user.id:
        return

    try:
        # Allows the owner to enable debug mode
        if message.content.startswith("$debug") and message.author.id == config.OWNER:
            if not config.DEBUG_BOT:
                debugging = not debugging
                await message.channel.send("Debugging {}".format("enabled" if debugging else "disabled"))
                return

        # If debugging, the real bot should ignore the owner
        if debugging and message.author.id == config.OWNER:
            return
        # The debug bot should only ever obey the owner
        # Debug bot doesn't care about debug status. If it's running, it assumes it's debugging
        elif config.DEBUG_BOT and message.author.id != config.OWNER:
            return

        # If bouncer detects a private DM sent to it
        if type(message.channel) is discord.channel.DMChannel:
            ts = message.created_at.strftime('%Y-%m-%d %H:%M:%S')

            # Store who the most recent user was, for $reply ^
            am.set_recent_reply(message.author)

            content = Utils.combineMessage(message)
            mes = "**{}#{}** (ID: {}): {}".format(message.author.name, message.author.discriminator, message.author.id, content)

            # If not blocked, send message along to specified mod channel
            if not bu.is_in_blocklist(message.author.id):
                chan = client.get_channel(config.VALID_INPUT_CHANS[0])
                logMes = await chan.send(mes)

                # Lets also add/update them in answering machine
                mes_link = Utils.get_mes_link(logMes)
                username = "{}#{}".format(message.author.name, message.author.discriminator)

                mes_entry = waiting.AnsweringMachineEntry(username, message.created_at, content, mes_link)
                am.update_entry(message.author.id, mes_entry)

        # Temporary - notify if UB3R-BOT has removed something on its word censor
        elif (message.author.id == 85614143951892480 and message.channel.id == 233039273207529472) and ("Word Censor Triggered" in message.content) and not config.DEBUG_BOT:
            mes = "Uh oh, looks like the censor might've been tripped.\n{}".format(Utils.get_mes_link(message))
            chan = client.get_channel(config.VALID_INPUT_CHANS[0])
            await chan.send(mes)

        # If a user pings bouncer, log into mod channel
        elif client.user in message.mentions:
            content = Utils.combineMessage(message)
            mes = "**{}#{}** (ID: {}) pinged me in <#{}>: {}".format(message.author.name, message.author.discriminator, message.author.id, message.channel.id, content)
            mes += "\n{}".format(Utils.get_mes_link(message))
            chan = client.get_channel(config.VALID_INPUT_CHANS[0])
            await chan.send(mes)

        # Functions in this category are those where we care that the user has the correct roles, but don't care about which channel they're invoked in
        elif Utils.checkRoles(message.author, config.VALID_ROLES):
            # Functions in this category must have both the correct roles, and also be invoked in specified channels
            if message.channel.id in config.VALID_INPUT_CHANS:
                cmd = Utils.get_command(message.content)
                # Print help message
                if cmd == "$help":
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
                    await message.channel.send(helpMes)
                elif cmd in FUNC_DICT:
                    func = FUNC_DICT[cmd][0]
                    arg = FUNC_DICT[cmd][1]
                    await func(message, arg)
                elif cmd == "$update":
                    # Update will call `git pull`, then kill the program so it automatically restarts
                    if message.author.id == config.OWNER:
                        await message.channel.send("Updating and restarting...")
                        subprocess.call(["git", "pull"])
                        sys.exit()
                    else:
                        await message.channel.send("Who do you think you are.")
                        return
                elif cmd == "$graph":
                    # Generates two plots to visualize moderation activity trends
                    import Visualize # Import here to avoid debugger crashing from matplotlib issue
                    Visualize.genUserPlot()
                    Visualize.genMonthlyPlot()
                    with open("../private/user_plot.png", 'rb') as f:
                        await message.channel.send(file=discord.File(f))

                    with open("../private/month_plot.png", 'rb') as f:
                        await message.channel.send(file=discord.File(f))
                elif cmd == "$uptime":
                    out = tk.uptime()
                    await message.channel.send(out)
                elif message.content.startswith("$waiting"):
                    output = am.gen_waiting_list()
                    await message.channel.send(output)
                elif message.content.startswith("$clear"):
                    am.clear_entries()
                    await message.channel.send("Waiting queue has been cleared")

    except discord.errors.HTTPException as e:
        print("HTTPException: {}", e)
        pass

client.run(config.DISCORD_KEY)
