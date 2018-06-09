"""
A Discord moderation bot, originally made for the Stardew Valley server
Written by aquova, 2018
https://github.com/aquova/bouncer
"""

import discord, json, sqlite3, datetime, asyncio, os
import Utils

# Reading values from config file
with open('config.json') as config_file:
    cfg = json.load(config_file)

# Configuring preferences
discordKey = str(cfg['discord'])
validInputChannels = cfg['channels']['listening']
logChannel = str(cfg['channels']['log'])
validRoles = cfg['roles']

sendBanDM = (cfg['DM']['ban'].upper() == "TRUE")
sendWarnDM = (cfg['DM']['warn'].upper() == "TRUE")

client = discord.Client()

# Create needed database, if doesn't exist
sqlconn = sqlite3.connect('sdv.db')
sqlconn.execute("CREATE TABLE IF NOT EXISTS badeggs (dbid INT PRIMARY KEY, id INT, username TEXT, num INT, date DATE, message TEXT, staff TEXT, post INT);")
sqlconn.execute("CREATE TABLE IF NOT EXISTS blocks (id TEXT);")
sqlconn.commit()
sqlconn.close()

warnThreshold = 3
lastCheck = datetime.datetime.fromtimestamp(1) # Create a new datetime object of ~0
checkCooldown = datetime.timedelta(minutes=5)

# Containers to store needed information in memory
recentBans = {}
blockList = []

# Logs current user count every hour into 'stats.csv'
async def logData():
    currentTime = datetime.datetime.utcnow()
    sdv = client.get_server(cfg['server'])
    with open('stats.csv', 'a') as openFile:
        openFile.write("{},{}\n".format(currentTime, sdv.member_count))

# Searches the database for the specified user, given a message
# m: Discord message object
async def userSearch(m):
    u = Utils.getID(m)
    # If message wasn't an ID, check if it's a username
    if u == None:
        u = Utils.parseUsername(m)

    member = discord.utils.get(m.server.members, id=u)
    if (u != None):
        sqlconn = sqlite3.connect('sdv.db')
        searchResults = sqlconn.execute("SELECT username, num, date, message, staff FROM badeggs WHERE id=?", [u]).fetchall()
        sqlconn.commit()
        sqlconn.close()

        if searchResults == []:
            if member != None:
                await client.send_message(m.channel, "User {}#{} was not found in the database\n".format(member.name, member.discriminator))
            else:
                await client.send_message(m.channel, "That user was not found in the database or in the server.")
        else:
            if member != None:
                out = "User {}#{} was found with the following infractions\n".format(member.name, member.discriminator)
            else:
                out = "That user was found with the following infractions:\n"
            for item in searchResults:
                if item[1] == 0:
                    out += "[{}] **{}** - Banned by {} - {}\n".format(Utils.formatTime(item[2]), item[0], item[4], item[3])
                else:
                    out += "[{}] **{}** - Warning #{} by {} - {}\n".format(Utils.formatTime(item[2]), item[0], item[1], item[4], item[3])
                if item[1] == warnThreshold:
                    out += "They have received {} warnings, it is recommended that they be banned.\n".format(warnThreshold)
            await client.send_message(m.channel, out)
    else:
        await client.send_message(m.channel, "I was unable to find a user by that name")

# Note a warn or ban for a user
# m: Discord message object
# Ban: Boolean, true for ban, false for warn
async def logUser(m, ban):
    # Attempt to get ID from message
    uid = Utils.getID(m)
    # If unable, treat it as a username
    if uid == None:
        uid = Utils.parseUsername(m)
    # If still unable, send error
    if uid == None:
        await client.send_message(m.channel, "I wasn't able to understand that message `$warn/ban USER message`")
        return

    u = discord.utils.get(m.server.members, id=uid)
    sqlconn = sqlite3.connect('sdv.db')
    if (ban):
        count = 0
    else:
        count = sqlconn.execute("SELECT COUNT(*) FROM badeggs WHERE id=?", [uid]).fetchone()[0] + 1
    globalcount = sqlconn.execute("SELECT COUNT(*) FROM badeggs").fetchone()[0]
    currentTime = datetime.datetime.utcnow()

    # User info is known
    if u != None: 
        params = [globalcount + 1, uid, "{}#{}".format(u.name, u.discriminator), count, currentTime, Utils.removeCommand(m.content), m.author.name]
    # User not found in server, but found in database
    elif u == None and count > 1: 
        searchResults = sqlconn.execute("SELECT username FROM badeggs WHERE id=?", [uid]).fetchall()
        params = [globalcount + 1, uid, searchResults[0][0], count, currentTime, Utils.removeCommand(m.content), m.author.name]
    # User has been banned since bot power on
    elif uid in recentBans: 
        params = [globalcount + 1, uid, recentBans[uid][0], count, currentTime, Utils.removeCommand(m.content), m.author.name]
    # User info is unknown
    else: 
        params = [globalcount + 1, uid, "ID: {}".format(uid), count, currentTime, Utils.removeCommand(m.content), m.author.name]
        await client.send_message(m.channel, "I wasn't able to find a username for that user, but whatever, I'll log them anyway.")

    # Generate message for log channel
    if ban:
        logMessage = "[{}] **{}** - Banned by {} - {}\n".format(Utils.formatTime(currentTime), params[2],  m.author.name, Utils.removeCommand(m.content))
    else:
        logMessage = "[{}] **{}** - Warning #{} by {} - {}\n".format(Utils.formatTime(currentTime), params[2], count, m.author.name, Utils.removeCommand(m.content))
    
    # Send message to log channel
    try:
        logMesID = await client.send_message(client.get_channel(logChannel), logMessage)
    except discord.errors.InvalidArgument:
        await client.send_message(m.channel, "The logging channel has not been set up in `config.json`. In order to have a visual record, please specify a channel ID.")
        logMesID = 0

    # Send ban recommendation, if needed
    if (count >= warnThreshold and ban == False):
        logMessage += "This user has received {} warnings or more. It is recommened that they be banned.".format(warnThreshold)
    await client.send_message(m.channel, logMessage)

    # Send a DM to the user
    try:
        if u != None:
            if ban and sendBanDM:
                mes = Utils.removeCommand(m.content)
                if mes != "":
                    await client.send_message(u, "You have been banned from the Stardew Valley server for the following reason: {}. If you have any questions, feel free to DM one of the staff members.".format(mes))
                else:
                    await client.send_message(u, "You have been banned from the Stardew Valley server for violating one of our rules. If you have any questions, feel free to DM one of the staff members.")
            elif not ban and sendWarnDM:
                mes = Utils.removeCommand(m.content)
                if mes != "":
                    await client.send_message(u, "You have received Warning #{} in the Stardew Valley server for the following reason: {}. If you have any questions, feel free to DM one of the staff members.".format(count, mes))
                else:
                    await client.send_message(u, "You have received Warning #{} in the Stardew Valley server for violating one of our rules. If you have any questions, feel free to DM one of the staff members.".format(count))

    # I don't know if any of these are ever getting tripped
    except discord.errors.Forbidden:
        await client.send_message(m.channel, "ERROR: I am not allowed to DM the user. It is likely that they are not accepting DM's from me.")
    except discord.errors.HTTPException as e:
        await client.send_message(m.channel, "ERROR: While attempting to DM, there was an unexpected error. Tell aquova this: {}".format(e))
    except discord.errors.NotFound:
        await client.send_message(m.channel, "ERROR: I was unable to find the user to DM. I'm unsure how this can be the case, unless their account was deleted")

    # Update database
    params.append(logMesID.id)
    sqlconn.execute("INSERT INTO badeggs (dbid, id, username, num, date, message, staff, post) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", params)
    sqlconn.commit()
    sqlconn.close()

# Removes last database entry for specified user
# m: Discord message object
async def removeError(m):
    # Try to get ID
    uid = Utils.getID(m)
    # If no ID, then try parsing username for ID
    if uid == None:
        uid = Utils.parseUsername(m)
    # This looks stupid, there's probably a slicker way to write this
    if uid == None:
        await client.send_message(m.channel, "I wasn't able to understand that message `$remove USER`")
        return

    # Find most recent entry in database for specified user
    sqlconn = sqlite3.connect('sdv.db')
    searchResults = sqlconn.execute("SELECT dbid, username, num, date, message, staff, post FROM badeggs WHERE id=?", [uid]).fetchall()
    if searchResults == []:
        await client.send_message(m.channel, "That user was not found in the database.")
    else:
        item = searchResults[-1]
        sqlconn.execute("REPLACE INTO badeggs (dbid, id, username, num, date, message, staff, post) VALUES (?, NULL, NULL, NULL, NULL, NULL, NULL, NULL)", [item[0]])
        out = "The following log was deleted:\n"
        if item[2] == 0:
            out += "[{}] **{}** - Banned by {} - {}\n".format(Utils.formatTime(item[3]), item[1], item[5], item[4])
        else:
            out += "[{}] **{}** - Warning #{} by {} - {}\n".format(Utils.formatTime(item[3]), item[1], item[2], item[5], item[4])
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
async def blockUser(message, block):
    global blockList
    uid = Utils.getID(message)
    if uid == None:
        await client.send_message(message.channel, "That was not a valid user ID")
        return
    sqlconn = sqlite3.connect('sdv.db')
    if block:
        if uid in blockList:
            await client.send_message(message.channel, "Um... That user was already blocked...")
        else:
            sqlconn.execute("INSERT INTO blocks (id) VALUES (?)", [uid])
            blockList.append(uid)
            await client.send_message(message.channel, "I have now blocked {}. Their messages will no longer display in chat, but they will be logged for later review.".format(uid))
    else:
        if uid not in blockList:
            await client.send_message(message.channel, "That user hasn't been blocked...")
        else:
            sqlconn.execute("DELETE FROM blocks WHERE id=?", [uid])
            blockList.remove(uid)
            await client.send_message(message.channel, "I have now unblocked {}. You will once again be able to hear their dumb bullshit in chat.".format(uid))
    sqlconn.commit()
    sqlconn.close()

# Special function made for SDV multiplayer beta release
# If matching phrase is posted, then post link to bug submission thread
async def checkForBugs(message):
    global lastCheck
    if ("BUG" in message.content.upper() and ("REPORT" in message.content.upper() or "FOUND" in message.content.upper())):
        if str(message.channel.id) in ["440552475913748491", "137345719668310016", "189945533861724160"]:
            await client.send_message(message.channel, "Did I hear someone say they found a MP bug? :bug:\nIf you wanna help out development of Stardew Valley, there's a link you can send your bug reports: <https://community.playstarbound.com/threads/stardew-valley-multiplayer-beta-known-issues-fixes-2.145034/>")
            lastCheck = datetime.datetime.utcnow()

@client.event
async def on_ready():
    global blockList
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)

    sqlconn = sqlite3.connect('sdv.db')
    blockDB = sqlconn.execute("SELECT * FROM blocks").fetchall()
    blockList = [x[0] for x in blockDB]
    sqlconn.close()

    # TODO: Have it wait until the top of the hour before logging
    while True:
        await logData()
        await asyncio.sleep(3600) # Sleep for 1 hour

@client.event
async def on_member_ban(member):
    global recentBans
    recentBans[member.id] = ["{}#{}".format(member.name, member.discriminator)]

@client.event
async def on_member_remove(member):
    # I know they aren't banned, but still we may want to log someone after they leave
    global recentBans
    recentBans[member.id] = ["{}#{}".format(member.name, member.discriminator)]

@client.event
async def on_message(message):
    global validInputChannels
    global logChannel
    if message.author.id != client.user.id:
        try:
            if message.channel.is_private:
                if message.author.id in blockList:
                    ts = message.timestamp.strftime('%Y-%m-%d %H:%M:%S')
                    with open("DMs.txt", 'a', encoding='utf-8') as openFile:
                        openFile.write("{} <ID: {}> {}\n".format(ts, "{}#{}".format(message.author.name, message.author.discriminator), message.content))
                else:
                    mes = "User {}#{} has sent me a private message: {}".format(message.author.name, message.author.discriminator, message.content)
                    await client.send_message(client.get_channel(validInputChannels[0]), mes)

            if (message.channel.id in validInputChannels) and Utils.checkRoles(message.author, validRoles):
                if message.content.startswith("$search"):
                    await userSearch(message)
                elif message.content.startswith("$warn"):
                    await logUser(message, False)
                elif message.content.startswith("$ban"):
                    await logUser(message, True)
                elif message.content.startswith("$remove"):
                    await removeError(message)
                elif message.content.startswith("$block"):
                    await blockUser(message, True)
                elif message.content.startswith("$unblock"):
                    await blockUser(message, False)
                elif message.content.startswith('$help'):
                    helpMes = "Issue a warning: `$warn USER message`\nLog a ban: `$ban USER reason`\nSearch for a user: `$search USER`\nRemove a user's last log: `$remove USER`\nStop a user from sending DMs to us: `$block/$unblock USERID`\nDMing users when they are banned is `{}`\nDMing users when they are warned is `{}`".format(sendBanDM, sendWarnDM)
                    await client.send_message(message.channel, helpMes)

                elif message.content.startswith("!search"):
                    await client.send_message(message.channel, "Aero made me switch it to `$search`...")
                elif message.content.startswith("!warn"):
                    await client.send_message(message.channel, "Aero made me switch it to `$warn`...")
                elif message.content.startswith("!ban"):
                    await client.send_message(message.channel, "Aero made me switch it to `$ban`...")
                elif message.content.startswith("!remove"):
                    await client.send_message(message.channel, "Aero made me switch it to `$remove`...")

            # A five minute cooldown for responding to people who mention bug reports
            if (datetime.datetime.utcnow() - lastCheck > checkCooldown):
                await checkForBugs(message)
        except discord.errors.HTTPException:
            pass

client.run(discordKey)
