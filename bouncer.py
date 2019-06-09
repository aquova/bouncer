"""
Bouncer
Written by aquova, 2018-2019
https://github.com/aquova/bouncer
"""

import discord, json, sqlite3, datetime, asyncio, os, subprocess, sys
import Utils
from User import User

# Reading values from config file
with open('config.json') as config_file:
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

client = discord.Client()
startTime = 0

charLimit = 2000

# Notes on database structure:
# Most of the columns are self explanitory
# num column is the category of the infraction
# 0: Ban
# >0: The number of the warning
# -1: Note
# -2: Kick
# -3: Unban

sqlconn = sqlite3.connect('sdv.db')
sqlconn.execute("CREATE TABLE IF NOT EXISTS badeggs (dbid INT PRIMARY KEY, id INT, username TEXT, num INT, date DATE, message TEXT, staff TEXT, post INT);")
sqlconn.execute("CREATE TABLE IF NOT EXISTS blocks (id TEXT);")
sqlconn.execute("CREATE TABLE IF NOT EXISTS staffLogs (staff TEXT PRIMARY KEY, bans INT, warns INT);")
sqlconn.execute("CREATE TABLE IF NOT EXISTS monthLogs (month TEXT PRIMARY KEY, bans INT, warns INT);")
sqlconn.commit()
sqlconn.close()

warnThreshold = 3
reviewThreshold = 6 # In months

# Containers to store needed information in memory
recentBans = {}
blockList = []
recentReply = None

helpInfo = {'$WARN':       '`$warn USER reason`',
            '$BAN':        '`$ban USER reason`',
            '$UNBAN':      '`$unban USER reason`',
            '$KICK':       '`$kick USER reason`',
            '$SEARCH':     '`$search USER`',
            '$NOTE':       '`$note USER message',
            '$REMOVE':     '`$remove USER',
            '$BLOCK':      '`$block USER`',
            '$UNBLOCK':    '`$unblock USER',
            '$REPLY':      '`$reply USER`'}

# This is basically a makeshift enum
class LogTypes:
    UNBAN = -3
    KICK = -2
    NOTE = -1
    BAN = 0
    WARN = 1

# Searches the database for the specified user, given a message
# m: Discord message object
async def userSearch(m):
    try:
        user = User(m, recentBans)
    except User.MessageError:
        await client.send_message(m.channel, "I wasn't able to find a user anywhere based on that message. `$search USER`")
        return

    searchResults = user.search()
    try:
        username = user.getName(recentBans)
        if searchResults == []:
            await client.send_message(m.channel, "User {} was not found in the database\n".format(username))
            return
    except User.MessageError:
        await client.send_message(m.channel, "That user was not found in the database or the server\n")
        return

    out = "User {} was found with the following infractions\n".format(username)
    for index, item in enumerate(searchResults):
        n = "{}. ".format(index+1)
        if item[1] == LogTypes.BAN:
            n += "[{}] **{}** - Banned by {} - {}\n".format(Utils.formatTime(item[2]), item[0], item[4], item[3])
        elif item[1] == LogTypes.NOTE:
            n += "[{}] **{}** - Note by {} - {}\n".format(Utils.formatTime(item[2]), item[0], item[4], item[3])
        elif item[1] == LogTypes.KICK:
            n += "[{}] **{}** - Kicked by {} - {}\n".format(Utils.formatTime(item[2]), item[0], item[4], item[3])
        elif item[1] == LogTypes.UNBAN:
            n += "[{}] **{}** - Unbanned by {} - {}\n".format(Utils.formatTime(item[2]), item[0], item[4], item[3])
        else:
            n += "[{}] **{}** - Warning #{} by {} - {}\n".format(Utils.formatTime(item[2]), item[0], item[1], item[4], item[3])

        if item[1] >= warnThreshold:
            n += "They have received {} warnings, it is recommended that they be banned.\n".format(warnThreshold)

        if len(out) + len(n) < charLimit:
            out += n
        else:
            await client.send_message(m.channel, out)
            out = n
    await client.send_message(m.channel, out)

# Note a warn or ban for a user
# m: Discord message object
async def logUser(m, state):
    try:
        user = User(m, recentBans)
    except User.MessageError:
        if state == LogTypes.NOTE:
            await client.send_message(m.channel, "I wasn't able to understand that message: `$note USER`")
        else:
            await client.send_message(m.channel, "I wasn't able to understand that message: `$log USER`")
        return

    sqlconn = sqlite3.connect('sdv.db')
    if state == LogTypes.WARN:
        count = sqlconn.execute("SELECT COUNT(*) FROM badeggs WHERE id=? AND num > 0", [user.id]).fetchone()[0] + 1
    else:
        count = state
    globalcount = sqlconn.execute("SELECT COUNT(*) FROM badeggs").fetchone()[0]
    currentTime = datetime.datetime.utcnow()

    try:
        username = user.getName(recentBans)
    except User.MessageError:
        username = "ID: " + str(user.id)
        await client.send_message(m.channel, "I wasn't able to find a username for that user, but whatever, I'll do it anyway.")

    mes = Utils.parseMessage(m.content, username)
    if len(m.attachments) != 0:
        for item in m.attachments:
            mes += '\n{}'.format(item['url'])

    if mes == "":
        await client.send_message(m.channel, "Please give a reason for why you want to log them.")
        return

    params = [globalcount + 1, user.id, username, count, currentTime, mes, m.author.name]

    # Generate message for log channel
    import Visualize
    if state == LogTypes.BAN:
        logMessage = "[{}] **{}** - Banned by {} - {}\n".format(Utils.formatTime(currentTime), params[2], m.author.name, mes)
        Visualize.updateCache(sqlconn, m.author.name, (1, 0), Utils.formatTime(currentTime))
    elif state == LogTypes.WARN:
        logMessage = "[{}] **{}** - Warning #{} by {} - {}\n".format(Utils.formatTime(currentTime), params[2], count, m.author.name, mes)
        Visualize.updateCache(sqlconn, m.author.name, (0, 1), Utils.formatTime(currentTime))
    elif state == LogTypes.KICK:
        logMessage = "[{}] **{}** - Kicked by {} - {}\n".format(Utils.formatTime(currentTime), params[2], m.author.name, mes)
    elif state == LogTypes.UNBAN:
        logMessage = "[{}] **{}** - Unbanned by {} - {}\n".format(Utils.formatTime(currentTime), params[2], m.author.name, mes)
        Visualize.updateCache(sqlconn, m.author.name, (-1, 0), Utils.formatTime(currentTime))
    else: # LogTypes.NOTE
        noteCount = sqlconn.execute("SELECT COUNT(*) FROM badeggs WHERE id=? AND num = -1", [user.id]).fetchone()[0] + 1
        logMessage = "Note #{} made for {}".format(noteCount, username)

    await client.send_message(m.channel, logMessage)

    # Send ban recommendation, if needed
    if (state == LogTypes.WARN and count >= warnThreshold):
        await client.send_message(m.channel, "This user has received {} warnings or more. It is recommended that they be banned.".format(warnThreshold))

    logMesID = 0
    if state != LogTypes.NOTE:
        # Send message to log channel
        try:
            logMes = await client.send_message(client.get_channel(logChannel), logMessage)
            logMesID = logMes.id
        except discord.errors.InvalidArgument:
            await client.send_message(m.channel, "The logging channel has not been set up in `config.json`. In order to have a visual record, please specify a channel ID.")

        # Send a DM to the user
        try:
            u = user.getMember()
            if u != None:
                if state == LogTypes.BAN and sendBanDM:
                    await client.send_message(u, "Hi there! You've been banned from the Stardew Valley Discord for violating the rules: {}. If you have any questions, you can send a message to the moderators via the sidebar at <https://www.reddit.com/r/StardewValley>, and they'll forward it to us.".format(mes))
                elif state == LogTypes.WARN and sendWarnDM:
                    await client.send_message(u, "Hi there! You received warning #{} in the Stardew Valley Discord for violating the rules: {}. Please review <#445729591533764620> and <#445729663885639680> for more info. If you have any questions, you can reply directly to this message to contact the staff.".format(count, mes))
                elif state == LogTypes.KICK and sendBanDM:
                    await client.send_message(u, "Hi there! You've been kicked from the Stardew Valley Discord for violating the following reason: {}. If you have any questions, you can send a message to the moderators via the sidebar at <https://www.reddit.com/r/StardewValley>, and they'll forward it to us.".format(mes))

        # I don't know if any of these are ever getting tripped
        except discord.errors.HTTPException as e:
            await client.send_message(m.channel, "ERROR: While attempting to DM, there was an unexpected error. Tell aquova this: {}".format(e))
        except discord.errors.Forbidden:
            await client.send_message(m.channel, "ERROR: I am not allowed to DM the user. It is likely that they are not accepting DM's from me.")
        except discord.errors.NotFound:
            await client.send_message(m.channel, "ERROR: I was unable to find the user to DM. I'm unsure how this can be the case, unless their account was deleted")

    # Update database
    params.append(logMesID)
    sqlconn.execute("INSERT INTO badeggs (dbid, id, username, num, date, message, staff, post) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", params)
    sqlconn.commit()
    sqlconn.close()

# Removes last database entry for specified user
# m: Discord message object
async def removeError(m):
    try:
        user = User(m, recentBans)
    except User.MessageError:
        await client.send_message(m.channel, "I wasn't able to understand that message: `$remove USER`")
        return

    # Needed for multi-word usernames
    try:
        username = user.getName(recentBans)
    except User.MessageError:
        username = str(user.id)

    mes = Utils.parseMessage(m.content, username)
    if mes == "":
        mes = "0"

    try:
        index = int(mes.split(" ")[0]) - 1
    except IndexError:
        index = -1
    except ValueError:
        await client.send_message(m.channel, "I don't know what `{}` is but I'm pretty sure it's not a number.".format(m.content.split(" ")[2]))
        return

    # Find most recent entry in database for specified user
    sqlconn = sqlite3.connect('sdv.db')
    searchResults = sqlconn.execute("SELECT dbid, username, num, date, message, staff, post FROM badeggs WHERE id=?", [user.id]).fetchall()

    if searchResults == []:
        await client.send_message(m.channel, "I couldn't find that user in the database")
    elif (index > len(searchResults) - 1) or index < -1:
        await client.send_message(m.channel, "I can't remove item number {}, there aren't that many for this user".format(index+1))
    else:
        item = searchResults[index]
        sqlconn.execute("REPLACE INTO badeggs (dbid, id, username, num, date, message, staff, post) VALUES (?, NULL, NULL, NULL, NULL, NULL, NULL, NULL)", [item[0]])

        import Visualize
        out = "The following log was deleted:\n"
        if item[2] == LogTypes.BAN:
            out += "[{}] **{}** - Banned by {} - {}\n".format(Utils.formatTime(item[3]), item[1], item[5], item[4])
            Visualize.updateCache(sqlconn, item[5], (-1, 0), Utils.formatTime(item[3]))
        elif item[2] == LogTypes.NOTE:
            out += "[{}] **{}** - Note by {} - {}\n".format(Utils.formatTime(item[3]), item[1], item[5], item[4])
        elif item[2] == LogTypes.UNBAN:
            out += "[{}] **{}** - Unbanned by {} - {}\n".format(Utils.formatTime(item[3]), item[1], item[5], item[4])
            Visualize.updateCache(sqlconn, item[5], (1, 0), Utils.formatTime(item[3]))
        elif item[2] == LogTypes.KICK:
            out += "[{}] **{}** - Kicked by {} - {}\n".format(Utils.formatTime(item[3]), item[1], item[5], item[4])
        else:
            out += "[{}] **{}** - Warning #{} by {} - {}\n".format(Utils.formatTime(item[3]), item[1], item[2], item[5], item[4])
            Visualize.updateCache(sqlconn, item[5], (0, -1), Utils.formatTime(item[3]))
        await client.send_message(m.channel, out)

        # Search logging channel for matching post, and remove it
        if item[6] != 0:
            async for m in client.logs_from(client.get_channel(logChannel)):
                if str(m.id) == str(item[6]):
                    await client.delete_message(m)
                    break
    sqlconn.commit()
    sqlconn.close()

# Prevents DM from a specific user from being forwarded
# message: Discord message object
# block: Boolean, true for block, false for unblock
async def blockUser(m, block):
    global blockList
    try:
        user = User(m, recentBans)
    except User.MessageError:
        await client.send_message(m.channel, "I wasn't able to understand that message: `$block USER`")
        return

    sqlconn = sqlite3.connect('sdv.db')
    if block:
        if user.id in blockList:
            await client.send_message(m.channel, "Um... That user was already blocked...")
        else:
            sqlconn.execute("INSERT INTO blocks (id) VALUES (?)", [user.id])
            blockList.append(user.id)
            await client.send_message(m.channel, "I have now blocked {}. Their messages will no longer display in chat, but they will be logged for later review.".format(user.id))
    else:
        if user.id not in blockList:
            await client.send_message(m.channel, "That user hasn't been blocked...")
        else:
            sqlconn.execute("DELETE FROM blocks WHERE id=?", [user.id])
            blockList.remove(user.id)
            await client.send_message(m.channel, "I have now unblocked {}. You will once again be able to hear their dumb bullshit in chat.".format(user.id))
    sqlconn.commit()
    sqlconn.close()

# Sends a private message to the specified user
async def reply(m):
    if m.content.split(" ")[1] == "^":
        if recentReply != None:
            u = recentReply
        else:
            await client.send_message(m.channel, "Sorry, I have no previous user stored. Gotta do it the old fashioned way.")
            return
    else:
        try:
            user = User(m, recentBans)
        except User.MessageError:
            await client.send_message(m.channel, "I wasn't able to understand that message: `$reply USER`")
            return

        u = user.getMember()
    if u == None:
        await client.send_message(m.channel, "Sorry, but they need to be in the server for me to message them")
        return
    try:
        mes = Utils.removeCommand(m.content)
        if len(m.attachments) != 0:
            for item in m.attachments:
                mes += '\n{}'.format(item['url'])
        ts = m.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        uname = "{}#{}".format(u.name, u.discriminator)
        with open("DMs.txt", 'a', encoding='utf-8') as openFile:
            openFile.write("{} - {} sent a DM to {}: {}\n".format(ts, m.author.name, uname, mes))
        await client.send_message(u, "A message from the SDV staff: {}".format(mes))
        await client.send_message(m.channel, "Message sent to {}.".format(uname))

    # I don't know if any of these are ever getting tripped
    except discord.errors.HTTPException as e:
        await client.send_message(m.channel, "ERROR: While attempting to DM, there was an unexpected error. Tell aquova this: {}".format(e))
    except discord.errors.Forbidden:
        await client.send_message(m.channel, "ERROR: I am not allowed to DM the user. It is likely that they are not accepting DM's from me.")
    except discord.errors.NotFound:
        await client.send_message(m.channel, "ERROR: I was unable to find the user to DM. I'm unsure how this can be the case, unless their account was deleted")

async def notebook(m):
    sqlconn = sqlite3.connect('sdv.db')
    allNotes = sqlconn.execute("SELECT * FROM badeggs WHERE num=-1").fetchall()
    sqlconn.commit()
    sqlconn.close()

    with open("notes.txt", "w") as f:
        for item in allNotes:
            note = "[{}] **{}** - Note by {} - {}\n".format(Utils.formatTime(item[4]), item[2], item[6], item[5])
            f.write(note)

    await client.send_message(m.channel, "Your notes, as requested.")

    await client.send_file(m.channel, fp='./notes.txt')

# Posts the usernames of all users whose oldest logs are older than reviewThreshold
async def userReview(channel):
    # There's probably a clever way to have these first two arrays merged
    usernames = []
    ids = []
    tooNew = []
    sqlconn = sqlite3.connect("sdv.db")
    # Reverse order so newest logs are checked/eliminated first
    allLogs = sqlconn.execute("SELECT id, username, date, num FROM badeggs WHERE num > -1").fetchall()[::-1]

    now = datetime.datetime.now()
    for log in allLogs:
        # Don't want to list users who have been banned
        if log[3] == 0:
            tooNew.append(log[0])
        if log[0] not in ids and log[0] not in tooNew:
            day = log[2].split(" ")[0]
            dateval = datetime.datetime.strptime(day, "%Y-%m-%d")
            testDate = dateval + datetime.timedelta(days=30*reviewThreshold)
            if testDate < now:
                ids.append(log[0])
                usernames.append(log[1])
            else:
                tooNew.append(log[0])

    sqlconn.close()

    mes = "These users had their most recent log greater than {} months ago.\n".format(reviewThreshold)
    # Reverse order so oldest are first
    for user in usernames[::-1]:
        # This gets past Discord's 2000 char limit
        if len(mes) + len(user) + 2 < charLimit:
            mes += "`{}`, ".format(user)
        else:
            await client.send_message(channel, mes)
            mes = "`{}`, ".format(user)

    await client.send_message(channel, mes)

async def uptime(channel):
    currTime = datetime.datetime.now()
    delta = currTime - startTime
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    mes = "I have been running for {} days, {} hours, and {} minutes".format(delta.days, hours, minutes)

    await client.send_message(channel, mes)

@client.event
async def on_ready():
    global blockList
    global startTime
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)

    startTime = datetime.datetime.now()

    sqlconn = sqlite3.connect('sdv.db')
    blockDB = sqlconn.execute("SELECT * FROM blocks").fetchall()
    blockList = [x[0] for x in blockDB]
    sqlconn.close()

    game_object = discord.Game(name="for your reports!", type=3)
    await client.change_presence(game=game_object)

@client.event
async def on_member_update(before, after):
    if before.nick != after.nick:
        if after.nick == None:
            mes = "**{}#{}** has reset their username".format(after.name, after.discriminator)
        else:
            new = after.nick
            mes = "**{}#{}** is now known as `{}`".format(after.name, after.discriminator, after.nick)
        await client.send_message(client.get_channel(systemLog), mes)
    elif before.roles != after.roles:
        if len(before.roles) > len(after.roles):
            missing = [r for r in before.roles if r not in after.roles]
            mes = "**{}#{}** had the role `{}` removed.".format(after.name, after.discriminator, missing[0])
        else:
            newRoles = [r for r in after.roles if r not in before.roles]
            mes = "**{}#{}** had the role `{}` added.".format(after.name, after.discriminator, newRoles[0])
        await client.send_message(client.get_channel(systemLog), mes)

@client.event
async def on_member_ban(member):
    global recentBans
    recentBans[member.id] = "{}#{}".format(member.name, member.discriminator)
    mes = "{}#{} has been banned.".format(member.name, member.discriminator)
    await client.send_message(client.get_channel(systemLog), mes)

@client.event
async def on_member_remove(member):
    # I know they aren't banned, but still we may want to log someone after they leave
    global recentBans
    recentBans[member.id] = "{}#{}".format(member.name, member.discriminator)
    mes = "**{}#{}** has left".format(member.name, member.discriminator)
    await client.send_message(client.get_channel(systemLog), mes)

@client.event
async def on_message_delete(message):
    mes = "**{}#{}** deleted in <#{}>: `{}`".format(message.author.name, message.author.discriminator, message.channel.id, message.content)
    if message.attachments != []:
        for item in message.attachments:
            mes += '\n' + item['url']
    await client.send_message(client.get_channel(systemLog), mes)

@client.event
async def on_message_edit(before, after):
    # This is to prevent embeding of content from triggering the log
    if before.content == after.content:
        return

    try:
        if len(before.content) + len(after.content) > 200:
            mes1 = "**{}#{}** modified in <#{}>: `{}`".format(before.author.name, before.author.discriminator, before.channel.id, before.content)
            mes2 = "to `{}`".format(after.content)
            if before.attachments != []:
                for item in before.attachments:
                    mes1 += '\n' + item['url']
            if after.attachments != []:
                for item in after.attachments:
                    mes2 += '\n' + item['url']
            await client.send_message(client.get_channel(systemLog), mes1)
            await client.send_message(client.get_channel(systemLog), mes2)
        else:
            mes = "**{}#{}** modified in <#{}>: `{}` to `{}`".format(before.author.name, before.author.discriminator, before.channel.id, before.content, after.content)
            if after.attachments != []:
                for item in after.attachments:
                    mes += '\n' + item['url']
            await client.send_message(client.get_channel(systemLog), mes)
    except discord.errors.HTTPException as e:
        print("Unknown error with editing message. This message was unable to post for this reason: {}\n".format(e))

@client.event
async def on_member_join(member):
    mes = "**{}#{}** has joined".format(member.name, member.discriminator)
    await client.send_message(client.get_channel(systemLog), mes)

@client.event
async def on_voice_state_update(before, after):
    if (after.voice.voice_channel == None):
        mes = "**{}#{}** has left voice channel {}".format(after.name, after.discriminator, before.voice.voice_channel.name)
        await client.send_message(client.get_channel(systemLog), mes)
    elif (before.voice.voice_channel == None):
        mes = "**{}#{}** has joined voice channel {}".format(after.name, after.discriminator, after.voice.voice_channel.name)
        await client.send_message(client.get_channel(systemLog), mes)

@client.event
async def on_message(message):
    global recentReply
    if message.author.id == client.user.id:
        return
    try:
        # If they sent a private DM to bouncer
        if message.channel.is_private:
            # Regardless of blocklist or not, log their messages
            ts = message.timestamp.strftime('%Y-%m-%d %H:%M:%S')

            # Store who the most recent user was, for $reply ^
            recentReply = message.author

            mes = "**{}#{}** (ID: {}): {}".format(message.author.name, message.author.discriminator, message.author.id, message.content)
            if message.attachments != []:
                for item in message.attachments:
                    mes += '\n' + item['url']

            with open("DMs.txt", 'a', encoding='utf-8') as openFile:
                openFile.write("{} - {}\n".format(ts, mes))
            await client.send_message(client.get_channel(validInputChannels[0]), mes)

        # Temporary - notify if UB3R-BOT has removed something on its word censor
        elif (message.author.id == "85614143951892480" and message.channel.id == "233039273207529472") and ("Word Censor Triggered" in message.content):
            mes = "Uh oh, looks like the censor might've been tripped.\nhttps://discordapp.com/channels/{}/{}/{}".format(message.server.id, message.channel.id, message.id)
            await client.send_message(client.get_channel(validInputChannels[0]), mes)

        # If a user pings bouncer
        elif client.user in message.mentions:
            mes = "**{}#{}** (ID: {}) pinged me in <#{}>: {}".format(message.author.name, message.author.discriminator, message.author.id, message.channel.id, message.content)
            if message.attachments != []:
                for item in message.attachments:
                    mes += '\n' + item['url']
            mes += "\nhttps://discordapp.com/channels/{}/{}/{}".format(message.server.id, message.channel.id, message.id)
            await client.send_message(client.get_channel(validInputChannels[0]), mes)

        # If they have privledges to access bouncer functions
        elif (message.channel.id in validInputChannels) and Utils.checkRoles(message.author, validRoles):
            if len(message.content.split(" ")) == 1:
                if message.content.upper() == "$HELP":
                    helpMes = "Issue a warning: `$warn USER message`\nLog a ban: `$ban USER reason`\nLog an unbanning: `$unban USER reason`\nLog a kick: `$kick USER reason`\nSearch for a user: `$search USER`\nCreate a note about a user: `$note USER message`\nShow all notes: `$notebook`\nRemove a user's last log: `$remove USER index(optional)`\nStop a user from sending DMs to us: `$block/$unblock USERID`\nReply to a user in DMs: `$reply USERID` - To reply to the most recent DM: `$reply ^`\nPlot warn/ban stats: `$graph`\nReview which users have old logs: `$review`\nView bot uptime: `$uptime`\nDMing users when they are banned is `{}`\nDMing users when they are warned is `{}`".format(sendBanDM, sendWarnDM)
                    await client.send_message(message.channel, helpMes)
                elif message.content.upper() == "$NOTEBOOK":
                    # await client.send_message(message.channel, "I've disabled notebook for now. You know why.")
                    await notebook(message)
                elif message.content.upper() in helpInfo.keys():
                    await client.send_message(message.channel, helpInfo[message.content.upper()])
                elif message.content.upper() == "$UPDATE":
                    if message.author.id == cfg["owner"]:
                        await client.send_message(message.channel, "Updating and restarting...")
                        subprocess.call(["git", "pull"])
                        sys.exit()
                    else:
                        await client.send_message(message.channel, "Who do you think you are.")
                        return
                elif message.content.upper() == "$GRAPH":
                    import Visualize # Import here to avoid debugger crashing from matplotlib issue
                    Visualize.genUserPlot()
                    Visualize.genMonthlyPlot()
                    await client.send_file(message.channel, fp='./user_plot.png')
                    await client.send_file(message.channel, fp='./month_plot.png')
                elif message.content.upper() == "$REVIEW":
                    await userReview(message.channel)
                elif message.content.upper() == "$UPTIME":
                    await uptime(message.channel)
                return

            # This if/elif thing isn't ideal, but it's by far the simpliest way
            if message.content.startswith("$search"):
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
                await removeError(message)
            elif message.content.startswith("$block"):
                await blockUser(message, True)
            elif message.content.startswith("$unblock"):
                await blockUser(message, False)
            elif message.content.startswith("$reply"):
                await reply(message)
            elif message.content.startswith("$note"):
                await logUser(message, LogTypes.NOTE)

    except discord.errors.HTTPException:
        pass

try:
    client.run(discordKey)
except CancelledError:
    print("CancelledError occurred")
    pass
except ConnectionResetError:
    print("ConnectionResetError occurred")
    pass
