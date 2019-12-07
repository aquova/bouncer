# Bouncer
# Written by aquova, 2018-2019
# https://github.com/aquova/bouncer

import discord, json, sqlite3, datetime, asyncio, os, subprocess, sys
import Utils
from User import User
from Utils import DATABASE_PATH, LogTypes
from Hunt import Hunter

# Reading values from config file
with open('private/config.json') as config_file:
    cfg = json.load(config_file)

# Configuring preferences
discordKey = cfg['discord']
# The first entry in validInputChannels is the one DMs and censor warnings are sent
validInputChannels = cfg['channels']['listening']
# Channel to save notes/warns/etc
logChannel = cfg['channels']['log']
# Channel to save system logs - leaves, bans, joins, etc
systemLog = cfg['channels']['syslog']
validRoles = cfg['roles']

sendBanDM = (cfg['DM']['ban'].upper() == "ON")
sendWarnDM = (cfg['DM']['warn'].upper() == "ON")

# Determine if this is a debugging instance
debugBot = (cfg['debug'].upper() == "TRUE")
debugging = False

client = discord.Client()
# Used to determine uptime
startTime = 0

# Event hunt object
hunter = Hunter()

# Notes on database structure:
# Most of the columns are self explanitory
# num column is the category of the infraction
# 0: Ban
# >0: The number of the warning
# -1: Note
# -2: Kick
# -3: Unban

# Create database and tables, if not created already
sqlconn = sqlite3.connect(DATABASE_PATH)
sqlconn.execute("CREATE TABLE IF NOT EXISTS badeggs (dbid INT PRIMARY KEY, id INT, username TEXT, num INT, date DATE, message TEXT, staff TEXT, post INT);")
sqlconn.execute("CREATE TABLE IF NOT EXISTS blocks (id TEXT);")
sqlconn.execute("CREATE TABLE IF NOT EXISTS staffLogs (staff TEXT PRIMARY KEY, bans INT, warns INT);")
sqlconn.execute("CREATE TABLE IF NOT EXISTS monthLogs (month TEXT PRIMARY KEY, bans INT, warns INT);")
sqlconn.execute("CREATE TABLE IF NOT EXISTS hunters (id INT PRIMARY KEY, username TEXT, count INT);")
sqlconn.commit()
sqlconn.close()

# Containers to store needed information in memory
recentBans = {}
blockList = []
recentReply = None

# Constants
# Discord has a 2000 message character limit
CHAR_LIMIT = 2000
# Add extra message if more than threshold number of warns
WARN_THRESHOLD = 3
# If older than threshold, add to review list, in months
REVIEW_THRESHOLD = 6

"""
User Search

Searches the database for the specified user, given a message

Input:
    m: Discord message object
"""
async def userSearch(m):
    # Attempt to generate user object
    try:
        user = User(m, recentBans)
    except User.MessageError:
        await m.channel.send("I wasn't able to find a user anywhere based on that message. `$search USER`")
        return

    # Get database values for given user
    searchResults = user.search()
    try:
        username = user.getName(recentBans)
        if searchResults == []:
            await m.channel.send("User {} was not found in the database\n".format(username))
            return
    except User.MessageError:
        await m.channel.send("That user was not found in the database or the server\n")
        return

    # Format output message
    out = "User {} was found with the following infractions\n".format(username)
    for index, item in enumerate(searchResults):
        # Enumerate each item
        n = "{}. ".format(index + 1)

        n += Utils.formatMessage(item)

        # If message becomes too long, send what we have and start a new post
        if len(out) + len(n) < CHAR_LIMIT:
            out += n
        else:
            await m.channel.send(out)
            out = n

    # Special notice if warns exceed threshold
    if len(searchResults) >= WARN_THRESHOLD:
        n += "They have received {} warnings, it is recommended that they be banned.\n".format(WARN_THRESHOLD)

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
    try:
        user = User(m, recentBans)
    except User.MessageError:
        if state == LogTypes.NOTE:
            await m.channel.send("I wasn't able to understand that message: `$note USER`")
        else:
            await m.channel.send("I wasn't able to understand that message: `$log USER`")
        return

    sqlconn = sqlite3.connect(DATABASE_PATH)
    # Calculate value for 'num' category in database
    # For warns, it's the newest number of warns, otherwise it's a special value
    if state == LogTypes.WARN:
        count = sqlconn.execute("SELECT COUNT(*) FROM badeggs WHERE id=? AND num > 0", [user.id]).fetchone()[0] + 1
    else:
        count = state
    globalcount = sqlconn.execute("SELECT COUNT(*) FROM badeggs").fetchone()[0]
    currentTime = datetime.datetime.utcnow()

    # Attempt to fetch the username for the user
    try:
        username = user.getName(recentBans)
    except User.MessageError:
        username = "ID: " + str(user.id)
        await m.channel.send("I wasn't able to find a username for that user, but whatever, I'll do it anyway.")

    # Generate log message, adding URLs of any attachments
    mes = Utils.parseMessage(m.content, username)
    if len(m.attachments) != 0:
        for item in m.attachments:
            mes += '\n{}'.format(item.url)

    # If they didn't give a message, abort
    if mes == "":
        await m.channel.send("Please give a reason for why you want to log them.")
        return

    # Update records for graphing
    import Visualize
    if state == LogTypes.BAN:
        Visualize.updateCache(sqlconn, m.author.name, (1, 0), Utils.formatTime(currentTime))
    elif state == LogTypes.WARN:
        Visualize.updateCache(sqlconn, m.author.name, (0, 1), Utils.formatTime(currentTime))
    elif state == LogTypes.NOTE:
        noteCount = sqlconn.execute("SELECT COUNT(*) FROM badeggs WHERE id=? AND num = -1", [user.id]).fetchone()[0] + 1
        logMessage = "Note #{} made for {}".format(noteCount, username)
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
            logs = user.search()
            for log in logs:
                sqlconn.execute("REPLACE INTO badeggs (dbid, id, username, num, date, message, staff, post) VALUES (?, NULL, NULL, NULL, NULL, NULL, NULL, NULL)", [log[5]])

            # C. Proceed with the unbanning
            logMessage = "[{}] **{}** - Unbanned by {} - {}\n".format(Utils.formatTime(currentTime), username, m.author.name, mes)
            Visualize.updateCache(sqlconn, m.author.name, (-1, 0), Utils.formatTime(currentTime))
        else:
            # Abort if they responded negatively
            await m.channel.send("Unban aborted.")
            sqlconn.close()
            return

    # Generate message for log channel
    formatArray = [None, m.author.id, username, state, currentTime, mes, m.author.name, None]
    logMessage = Utils.formatMessage(formatArray)
    await m.channel.send(logMessage)

    # Send ban recommendation, if needed
    if (state == LogTypes.WARN and count >= WARN_THRESHOLD):
        await m.channel.send("This user has received {} warnings or more. It is recommended that they be banned.".format(WARN_THRESHOLD))

    logMesID = 0
    # If we aren't noting, need to also write to log channel
    if state != LogTypes.NOTE:
        # Post to channel, keep track of message ID
        try:
            chan = client.get_channel(logChannel)
            logMes = await chan.send(logMessage)
            logMesID = logMes.id
        except discord.errors.InvalidArgument:
            # TODO: Someday make this optional?
            await m.channel.send("The logging channel has not been set up in `config.json`. In order to have a visual record, please specify a channel ID.")

        try:
            # Send a DM to the user
            u = user.getMember()
            if u != None:
                DMchan = u.dm_channel
                # If first time DMing, need to create channel
                if DMchan == None:
                    DMchan = await u.create_dm()

                # Only send DM when specified in configs
                if state == LogTypes.BAN and sendBanDM:
                    await DMchan.send("Hi there! You've been banned from the Stardew Valley Discord for violating the rules: `{}`. If you have any questions, you can send a message to the moderators via the sidebar at <https://www.reddit.com/r/StardewValley>, and they'll forward it to us.".format(mes))
                elif state == LogTypes.WARN and sendWarnDM:
                    await DMchan.send("Hi there! You received warning #{} in the Stardew Valley Discord for violating the rules: `{}`. Please review <#445729591533764620> and <#445729663885639680> for more info. If you have any questions, you can reply directly to this message to contact the staff.".format(count, mes))
                elif state == LogTypes.KICK and sendBanDM:
                    await DMchan.send("Hi there! You've been kicked from the Stardew Valley Discord for violating the following reason: `{}`. If you have any questions, you can send a message to the moderators via the sidebar at <https://www.reddit.com/r/StardewValley>, and they'll forward it to us.".format(mes))

        # Exception handling
        except discord.errors.HTTPException as e:
            await m.channel.send("ERROR: While attempting to DM, there was an unexpected error. Tell aquova this: {}".format(e))
        except discord.errors.Forbidden:
            await m.channel.send( "ERROR: I am not allowed to DM the user. It is likely that they are not accepting DM's from me.")
        except discord.errors.NotFound:
            await m.channel.send("ERROR: I was unable to find the user to DM. I'm unsure how this can be the case, unless their account was deleted")

    # Update database
    params = [globalcount + 1, user.id, username, count, currentTime, mes, m.author.name, logMesID]
    sqlconn.execute("INSERT INTO badeggs (dbid, id, username, num, date, message, staff, post) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", params)
    sqlconn.commit()
    sqlconn.close()

"""
Remove Error

Removes last database entry for specified user

Input:
    m: Discord message object
    edit: Boolean, signifies if this is a deletion (false) or an edit (true)
"""
async def removeError(m, edit):
    try:
        user = User(m, recentBans)
    except User.MessageError:
        if edit:
            await m.channel.send("I wasn't able to understand that message: `$remove USER [num] new_message`")
        else:
            await m.channel.send("I wasn't able to understand that message: `$remove USER [num]`")
        return

    # Special handling for multi-word usernames
    try:
        username = user.getName(recentBans)
    except User.MessageError:
        username = str(user.id)

    # If editing, and no message specified, abort.
    mes = Utils.parseMessage(m.content, username)
    if mes == "":
        if edit:
            await m.channel.send("You need to specify an edit message")
            return
        else:
            mes = "0"

    try:
        index = int(mes.split(" ")[0]) - 1
        mes = Utils.strip(mes)
    except (IndexError, ValueError):
        index = -1

    # Find most recent entry in database for specified user
    sqlconn = sqlite3.connect(DATABASE_PATH)
    searchResults = sqlconn.execute("SELECT dbid, id, username, num, date, message, staff, post FROM badeggs WHERE id=?", [user.id]).fetchall()

    # If no results in database found, can't modify
    if searchResults == []:
        await m.channel.send("I couldn't find that user in the database")
    # If invalid index given, yell
    elif (index > len(searchResults) - 1) or index < -1:
        await m.channel.send("I can't modify item number {}, there aren't that many for this user".format(index + 1))
    else:
        item = searchResults[index]
        import Visualize
        if edit:
            if item[3] == LogTypes.NOTE:
                currentTime = datetime.datetime.utcnow()
                # Make a copy of the original log, then modify a few fields
                params = list(item)
                params[4] = currentTime
                params[5] = mes
                params[6] = m.author.name
                sqlconn.execute("REPLACE INTO badeggs (dbid, id, username, num, date, message, staff, post) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", params)
                out = "The following log was edited:\n[{}] **{}** - Note by {} - {}\n".format(Utils.formatTime(item[4]), item[2], item[6], item[5])
                out = "The log now reads as follows:\n[{}] **{}** - Note by {} - {}\n".format(Utils.formatTime(params[4]), params[2], params[6], params[5])
                await m.channel.send(out)

                sqlconn.commit()
                sqlconn.close()
                return
            else:
                await m.channel.send("You can only edit notes for now")
                sqlconn.close()
                return

        # Everything after here is deletion
        sqlconn.execute("REPLACE INTO badeggs (dbid, id, username, num, date, message, staff, post) VALUES (?, NULL, NULL, NULL, NULL, NULL, NULL, NULL)", [item[0]])
        out = "The following log was deleted:\n"

        out += Utils.formatMessage(item)

        if item[3] == LogTypes.BAN:
            Visualize.updateCache(sqlconn, item[6], (-1, 0), Utils.formatTime(item[4]))
        elif item[3] == LogTypes.UNBAN:
            Visualize.updateCache(sqlconn, item[6], (1, 0), Utils.formatTime(item[4]))
        elif item[3] == LogTypes.WARN:
            Visualize.updateCache(sqlconn, item[6], (0, -1), Utils.formatTime(item[4]))
        await m.channel.send(out)

        # Search logging channel for matching post, and remove it
        try:
            if item[7] != 0:
                chan = client.get_channel(logChannel)
                m = await chan.fetch_message(item[7])
                await m.delete()
        # Print message if unable to find message to delete, but don't stop
        except HTTPException as e:
            print("Unable to find message to delete: {}", str(e))
    sqlconn.commit()
    sqlconn.close()

"""
Block User

Prevents DMs from a given user from being forwarded

Input:
    m: Discord message object
    block: Boolean, true for block, false for unblock
"""
async def blockUser(m, block):
    global blockList
    # Attempt to find user in database
    try:
        user = User(m, recentBans)
    except User.MessageError:
        await m.channel.send("I wasn't able to understand that message: `$block USER`")
        return

    # Store in the database that the given user is un/blocked
    # Also update current block list to match
    sqlconn = sqlite3.connect(DATABASE_PATH)
    if block:
        if user.id in blockList:
            await m.channel.send("Um... That user was already blocked...")
        else:
            sqlconn.execute("INSERT INTO blocks (id) VALUES (?)", [user.id])
            blockList.append(user.id)
            await m.channel.send("I have now blocked {}. Their messages will no longer display in chat, but they will be logged for later review.".format(user.id))
    else:
        if user.id not in blockList:
            await m.channel.send("That user hasn't been blocked...")
        else:
            sqlconn.execute("DELETE FROM blocks WHERE id=?", [user.id])
            blockList.remove(user.id)
            await m.channel.send("I have now unblocked {}. You will once again be able to hear their dumb bullshit in chat.".format(user.id))
    sqlconn.commit()
    sqlconn.close()

"""
Reply

Sends a private message to the specified user

Input:
    m: Discord message object
"""
async def reply(m):
    # If given '^' instead of user, message the last person to DM bouncer
    # Uses whoever DMed last since last startup, don't bother keeping in database or anything like that
    if m.content.split(" ")[1] == "^":
        if recentReply != None:
            u = recentReply
        else:
            await m.channel.send("Sorry, I have no previous user stored. Gotta do it the old fashioned way.")
            return
    else:
        # Otherwise, attempt to get object for the specified user
        try:
            user = User(m, recentBans)
        except User.MessageError:
            await m.channel.send("I wasn't able to understand that message: `$reply USER`")
            return

        u = user.getMember()
    # If we couldn't find anyone, then they aren't in the server, and can't be DMed
    if u == None:
        await m.channel.send("Sorry, but they need to be in the server for me to message them")
        return
    try:
        mes = Utils.removeCommand(m.content)
        # Add URLs for any attached messages into text body
        if len(m.attachments) != 0:
            for item in m.attachments:
                mes += '\n{}'.format(item.url)
        # Keep local log of all DMs
        ts = m.created_at.strftime('%Y-%m-%d %H:%M:%S')
        uname = "{}#{}".format(u.name, u.discriminator)
        with open("private/DMs.txt", 'a', encoding='utf-8') as openFile:
            openFile.write("{} - {} sent a DM to {}: {}\n".format(ts, m.author.name, uname, mes))

        DMchan = u.dm_channel
        # If first DMing, need to create DM channel
        if DMchan == None:
            DMchan = await u.create_dm()
        # Message sent to user
        await DMchan.send("A message from the SDV staff: {}".format(mes))
        # Notification of sent message to the senders
        await m.channel.send("Message sent to {}.".format(uname))

    # Exception handling
    except discord.errors.HTTPException as e:
        await m.channel.send("ERROR: While attempting to DM, there was an unexpected error. Tell aquova this: {}".format(e))
    except discord.errors.Forbidden:
        await m.channel.send("ERROR: I am not allowed to DM the user. It is likely that they are not accepting DM's from me.")
    except discord.errors.NotFound:
        await m.channel.send("ERROR: I was unable to find the user to DM. I'm unsure how this can be the case, unless their account was deleted")

"""
Notebook

Generate .txt file containing all notes from all users

Input:
    m: Discord message object
"""
async def notebook(m):
    sqlconn = sqlite3.connect(DATABASE_PATH)
    # Retreive all items in database that are notes
    allNotes = sqlconn.execute("SELECT * FROM badeggs WHERE num=-1").fetchall()
    sqlconn.commit()
    sqlconn.close()


    # Write to file kept in git ignored directory
    with open("private/notes.txt", "w") as f:
        for item in allNotes:
            # Very similar to formatting in Utils function, but with different array indexes
            note = "[{}] **{}** - Note by {} - {}\n".format(Utils.formatTime(item[4]), item[2], item[6], item[5])
            f.write(note)

    # Attach .txt file once compiled
    await m.channel.send("Your notes, as requested.")
    with open("./private/notes.txt", "r") as f:
        await m.channel.send(file=discord.File(f))


"""
User Review

Posts the usernames of all users whose oldest logs are older than REVIEW_THRESHOLD

Input:
    channel: Discord channel object request was made from
"""
async def userReview(channel):
    # Keep track both of users we want to review and those we don't, so we can skip over them
    tooOld = []
    tooNew = []
    sqlconn = sqlite3.connect(DATABASE_PATH)
    # Reverse order so newest logs are checked/eliminated first
    allLogs = sqlconn.execute("SELECT id, username, date, num FROM badeggs WHERE num > -1").fetchall()[::-1]

    now = datetime.datetime.now()
    for log in allLogs:
        # Store username and ID in tuple
        logTuple = (log[0], log[1])
        # Don't want to list users who have been banned
        if log[3] == 0:
            tooNew.append(log[0])
        # Only check users if they haven't been included/eliminated
        if logTuple not in tooOld and log[0] not in tooNew:
            day = log[2].split(" ")[0]
            dateval = datetime.datetime.strptime(day, "%Y-%m-%d")
            testDate = dateval + datetime.timedelta(days=30*REVIEW_THRESHOLD)
            if testDate < now:
                tooOld.append(logTuple)
            else:
                tooNew.append(log[0])

    sqlconn.close()

    mes = "These users had their most recent log greater than {} months ago.\n".format(REVIEW_THRESHOLD)
    # Reverse order so oldest are first
    for user in tooOld[::-1]:
        # If we hit Discord's character limit, post what we have and start a new message
        if len(mes) + len(user) + 2 < CHAR_LIMIT:
            mes += "`{}`, ".format(user[0])
        else:
            await channel.send(mes)
            mes = "`{}`, ".format(user[0])

    await channel.send(mes)

"""
Uptime

Posts the current uptime for the bot

Input:
    channel: Discord channel object from which the request was made
"""
async def uptime(channel):
    currTime = datetime.datetime.now()
    delta = currTime - startTime
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    mes = "I have been running for {} days, {} hours, and {} minutes".format(delta.days, hours, minutes)

    await channel.send(mes)

"""
On Ready

Occurs when Discord bot is first brought online
"""
@client.event
async def on_ready():
    global blockList
    global startTime
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)

    # Note the time for the uptime function
    startTime = datetime.datetime.now()

    # Load any users who were banned into memory
    sqlconn = sqlite3.connect(DATABASE_PATH)
    blockDB = sqlconn.execute("SELECT * FROM blocks").fetchall()
    blockList = [str(x[0]) for x in blockDB]
    sqlconn.close()

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
    if debugBot:
        return
    # If nickname has changed
    if before.nick != after.nick:
        # If they don't have an ending nickname, they reset to their actual username
        if after.nick == None:
            mes = "**{}#{}** has reset their username".format(after.name, after.discriminator)
        else:
            new = after.nick
            mes = "**{}#{}** is now known as `{}`".format(after.name, after.discriminator, after.nick)
        chan = client.get_channel(systemLog)
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
        chan = client.get_channel(systemLog)
        await chan.send(mes)

"""
On Member Ban

Occurs when a user is banned
"""
@client.event
async def on_member_ban(server, member):
    global recentBans
    # If debugging, don't process
    if debugBot:
        return
    # Keep a record of their banning, in case the log is made after they're no longer here
    recentBans[member.id] = "{}#{}".format(member.name, member.discriminator)
    mes = "**{}#{} ({})** has been banned.".format(member.name, member.discriminator, member.id)
    chan = client.get_channel(systemLog)
    await chan.send(mes)

"""
On Member Remove

Occurs when a user leaves the server
"""
@client.event
async def on_member_remove(member):
    global recentBans
    # If debugging, don't process
    if debugBot:
        return
    # Remember that the user has left, in case we want to log after they're gone
    recentBans[str(member.id)] = "{}#{}".format(member.name, member.discriminator)
    mes = "**{}#{} ({})** has left".format(member.name, member.discriminator, member.id)
    chan = client.get_channel(systemLog)
    await chan.send(mes)

"""
On Raw Reaction Add

Occurs when a reaction is applied to a message
Needs to be raw reaction so it can still get reactions after reboot
"""
@client.event
async def on_raw_reaction_add(payload):
    # If debugging, don't process
    if debugBot:
        return
    if payload.message_id == cfg["gatekeeper"]["message"] and payload.emoji.name == cfg["gatekeeper"]["emoji"]:
        # Raw payload just returns IDs, so need to iterate through connected servers to get server object
        # Since each bouncer instance will only be in one server, it should be quick.
        # If bouncer becomes general purpose (god forbid), may need to rethink this
        try:
            server = [x for x in client.guilds if x.id == payload.guild_id][0]
            new_role = discord.utils.get(server.roles, id=cfg["gatekeeper"]["role"])
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
    if debugBot:
        return
    # Don't allow bouncer to react to its own deleted messages
    if message.author.id == client.user.id:
        return
    mes = "**{}#{}** deleted in <#{}>: `{}`".format(message.author.name, message.author.discriminator, message.channel.id, message.content)
    # Adds URLs for any attachments that were included in deleted message
    # These will likely become invalid, but it's nice to note them anyway
    if message.attachments != []:
        for item in message.attachments:
            mes += '\n' + item.url
    chan = client.get_channel(systemLog)
    await chan.send(mes)

"""
On Message Edit

Occurs when a user edits a message
"""
@client.event
async def on_message_edit(before, after):
    # If debugging, don't process
    if debugBot:
        return
    # Prevent embedding of content from triggering the log
    if before.content == after.content:
        return
    try:
        # Since we note both the before and after message, it's possible we'll surpass Discord's character limit
        # In that case, break the message up into two parts
        # TODO: The code reusability of this can be improved
        if len(before.content) + len(after.content) > CHAR_LIMIT:
            mes1 = "**{}#{}** modified in <#{}>: `{}`".format(before.author.name, before.author.discriminator, before.channel.id, before.content)
            mes2 = "to `{}`".format(after.content)
            # Note URLs for any attachments
            if before.attachments != []:
                for item in before.attachments:
                    mes1 += '\n' + item.url
            if after.attachments != []:
                for item in after.attachments:
                    mes2 += '\n' + item.url
            chan = client.get_channel(systemLog)
            await chan.send(mes1)
            await chan.send(mes2)
        else:
            mes = "**{}#{}** modified in <#{}>: `{}` to `{}`".format(before.author.name, before.author.discriminator, before.channel.id, before.content, after.content)
            if after.attachments != []:
                for item in after.attachments:
                    mes += '\n' + item.url
            chan = client.get_channel(systemLog)
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
    if debugBot:
        return
    mes = "**{}#{} ({})** has joined".format(member.name, member.discriminator, member.id)
    chan = client.get_channel(systemLog)
    await chan.send(mes)

"""
On Voice State Update

Occurs when a user joins/leaves an audio channel
"""
@client.event
async def on_voice_state_update(member, before, after):
    # If debugging, don't process
    if debugBot:
        return
    if after.channel == None:
        mes = "**{}#{}** has left voice channel {}".format(member.name, member.discriminator, before.channel.name)
        chan = client.get_channel(systemLog)
        await chan.send(mes)
    elif before.channel == None:
        mes = "**{}#{}** has joined voice channel {}".format(member.name, member.discriminator, after.channel.name)
        chan = client.get_channel(systemLog)
        await chan.send(mes)

"""
On Reaction Add

Occurs when a reaction was added to a message
Only used for egg hunting
"""
@client.event
async def on_reaction_add(reaction, user):
    # Bouncer should not react to its own reactions
    if user.id == client.user.id:
        return

    # If hunting, process event
    if hunter.getWatchedChannel() == reaction.message.channel.id:
        hunter.addReaction(user)

"""
On Message

Occurs when a user posts a message
More or less the main function
"""
@client.event
async def on_message(message):
    global recentReply
    global debugging
    # Bouncer should not react to its own messages
    if message.author.id == client.user.id:
        return
    try:
        # Allows the owner to enable debug mode
        if message.content.startswith("$debug") and message.author.id == cfg['owner']:
            if not debugBot:
                debugging = not debugging
                await message.channel.send("Debugging {}".format("enabled" if debugging else "disabled"))
                return

        # If debugging, the real bot should ignore the owner
        if debugging and message.author.id == cfg['owner']:
            return
        # The debug bot should only ever obey the owner
        # Debug bot doesn't care about debug status. If it's running, it assumes it's debugging
        elif debugBot and message.author.id != cfg['owner']:
            return

        # If bouncer detects a private DM sent to it
        if type(message.channel) is discord.channel.DMChannel:
            ts = message.created_at.strftime('%Y-%m-%d %H:%M:%S')

            # Store who the most recent user was, for $reply ^
            recentReply = message.author

            mes = "**{}#{}** (ID: {}): {}".format(message.author.name, message.author.discriminator, message.author.id, message.content)
            if message.attachments != []:
                for item in message.attachments:
                    mes += '\n' + item.url

            # Regardless of blocklist or not, log their messages
            with open("private/DMs.txt", 'a', encoding='utf-8') as openFile:
                openFile.write("{} - {}\n".format(ts, mes))

            # If not blocked, send message along to specified mod channel
            if str(message.author.id) not in blockList:
                chan = client.get_channel(validInputChannels[0])
                await chan.send(mes)

        # Temporary - notify if UB3R-BOT has removed something on its word censor
        elif (message.author.id == 85614143951892480 and message.channel.id == 233039273207529472) and ("Word Censor Triggered" in message.content) and not debugBot:
            mes = "Uh oh, looks like the censor might've been tripped.\nhttps://discordapp.com/channels/{}/{}/{}".format(message.guild.id, message.channel.id, message.id)
            chan = client.get_channel(validInputChannels[0])
            await chan.send(mes)

        # If a user pings bouncer, log into mod channel
        elif client.user in message.mentions:
            mes = "**{}#{}** (ID: {}) pinged me in <#{}>: {}".format(message.author.name, message.author.discriminator, message.author.id, message.channel.id, message.content)
            if message.attachments != []:
                for item in message.attachments:
                    mes += '\n' + item.url
            mes += "\nhttps://discordapp.com/channels/{}/{}/{}".format(message.guild.id, message.channel.id, message.id)
            chan = client.get_channel(validInputChannels[0])
            await chan.send(mes)

        # Functions in this category are those where we care that the user has the correct roles, but don't care about which channel they're invoked in
        elif Utils.checkRoles(message.author, validRoles):
            # Special case for the egg hunt functions. We want only permitted roles to access them,
            # but their channel will always be new, so allow any channel access
            if message.content.startswith("$starthunt"):
                words = message.clean_content.split(" ")
                if len(words) != 2:
                    await message.channel.send("Invalid command. `$starthunt EMOJI`")
                    return
                hunter.setWatchedChannel(message.channel)
                mes = await message.channel.send("{}".format(words[1]))
                try:
                    emoji = words[1].split(":")[1]
                    emojiObject = [x for x in message.guild.emojis if x.name == emoji][0]
                    await mes.add_reaction(emojiObject)
                except IndexError:
                    emoji = words[1].replace(":", "")
                    await mes.add_reaction(emoji)
                await message.delete()
            elif message.content.startswith("$endhunt"):
                hunter.stopWatching()
                await message.channel.send("I hope your hunt has been victorious!")
            elif message.content.startswith("$gethunt"):
                hunter.export()
                with open("./private/hunters.csv", "r") as f:
                    await message.channel.send(file=discord.File(f))

            # Functions in this category must have both the correct roles, and also be invoked in specified channels
            elif message.channel.id in validInputChannels:
                # This if/elif thing isn't ideal, but it's by far the simpliest way to mimic a switch case
                # Print help message
                if message.content.upper() == "$HELP":
                    helpMes = (
                        "Issue a warning: `$warn USER message`\n"
                        "Log a ban: `$ban USER reason`\n"
                        "Log an unbanning: `$unban USER reason`\n"
                        "Log a kick: `$kick USER reason`\n"
                        "Search for a user: `$search USER`\n"
                        "Create a note about a user: `$note USER message`\n"
                        "Show all notes: `$notebook`\n"
                        "Remove a user's log: `$remove USER index(optional)`\n"
                        "Edit a user's note: `$edit USER index(optional) new_message`\n"
                        "Stop a user from sending DMs to us: `$block/$unblock USERID`\n"
                        "Reply to a user in DMs: `$reply USERID` - To reply to the most recent DM: `$reply ^`\n"
                        "Plot warn/ban stats: `$graph`\nReview which users have old logs: `$review`\n"
                        "View bot uptime: `$uptime`\n"
                        "DMing users when they are banned is `{}`\n"
                        "DMing users when they are warned is `{}`".format(sendBanDM, sendWarnDM)
                    )
                    await message.channel.send(helpMes)
                elif message.content.upper() == "$NOTEBOOK":
                    await notebook(message)
                elif message.content.upper() == "$UPDATE":
                    # Update will call `git pull`, then kill the program so it automatically restarts
                    if message.author.id == cfg["owner"]:
                        await message.channel.send("Updating and restarting...")
                        subprocess.call(["git", "pull"])
                        sys.exit()
                    else:
                        await message.channel.send("Who do you think you are.")
                        return
                elif message.content.upper() == "$GRAPH":
                    # Generates two plots to visualize moderation activity trends
                    import Visualize # Import here to avoid debugger crashing from matplotlib issue
                    Visualize.genUserPlot()
                    Visualize.genMonthlyPlot()
                    with open("./private/user_plot.png", 'rb') as f:
                        await message.channel.send(file=discord.File(f))

                    with open("./private/month_plot.png", 'rb') as f:
                        await message.channel.send(file=discord.File(f))
                elif message.content.upper() == "$REVIEW":
                    await userReview(message.channel)
                elif message.content.upper() == "$UPTIME":
                    await uptime(message.channel)
                elif message.content.upper() == "$GETROLES":
                    output = await Utils.fetchRoleList(message.guild)
                    await message.channel.send(output)
                elif message.content.startswith("$search"):
                    await userSearch(message)
                elif message.content.startswith("$warn"):
                    await logUser(message, LogTypes.WARN)
                elif message.content.startswith("$ban"):
                    await logUser(message, LogTypes.BAN)
                elif message.content.startswith("$kick"):
                    await logUser(message, LogTypes.KICK)
                elif message.content.startswith("$unban"):
                    await logUser(message, LogTypes.UNBAN)
                elif message.content.startswith("$remove"):
                    await removeError(message, False)
                elif message.content.startswith("$block"):
                    await blockUser(message, True)
                elif message.content.startswith("$unblock"):
                    await blockUser(message, False)
                elif message.content.startswith("$reply"):
                    await reply(message)
                elif message.content.startswith("$note"):
                    await logUser(message, LogTypes.NOTE)
                elif message.content.startswith("$edit"):
                    await removeError(message, True)

                # Debug functions only to be executed by the owner
                elif message.content.upper() == "$DUMPBANS" and message.author.id == cfg["owner"]:
                    output = await Utils.dumpBans(recentBans)
                    if output != "":
                        await message.channel.send(output)
                    else:
                        await message.channel.send("There has been no bans since I was rebooted.")

    except discord.errors.HTTPException as e:
        print("HTTPException: {}", e)
        pass

client.run(discordKey)
