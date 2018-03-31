"""
A Discord moderation bot, originally made for the Stardew Valley server
Written by aquova, 2018
https://github.com/aquova/bouncer
"""

import discord, json, sqlite3, datetime

with open('config.json') as config_file:
    cfg = json.load(config_file)

discordKey = str(cfg['discord'])
validInputChannels = cfg['channels']['listening']
logChannel = str(cfg['channels']['log'])
validRoles = cfg['roles']

if cfg['DM']['ban'].upper() == "TRUE":
    sendBanDM = True
else:
    sendBanDM = False

if cfg['DM']['warn'].upper() == "TRUE":
    sendWarnDM = True
else:
    sendWarnDM = False

client = discord.Client()

# Create needed database, if doesn't exist
sqlconn = sqlite3.connect('sdv.db')
sqlconn.execute("CREATE TABLE IF NOT EXISTS badeggs (dbid INT PRIMARY KEY, id INT, username TEXT, num INT, date DATE, message TEXT, staff TEXT);")
sqlconn.commit()
sqlconn.close()

warnThreshold = 3

def removeCommand(m):
    tmp = m.split(" ")[2:]
    return " ".join(tmp)

def formatTime(t):
    # Input t is of the form: YYYY-MM-DD HH:MM:SS.SSSSSS
    date = str(t).split(" ")[0]
    pieces = date.split("-")
    # output is of the form DD/MM/YYYY
    european = "{}/{}/{}".format(pieces[2], pieces[1], pieces[0])
    return european

def checkRoles(user):
    if len(validRoles) == 1 and validRoles[0] == "":
        return True
    for role in user.roles:
        for r in validRoles:
            if role.id == r:
                return True
    return False

def getID(message):
    # If message contains one mention, return its ID
    if len(message.mentions) == 1:
        return message.mentions[0].id
    # Otherwise, check if second word of message is an ID
    test = message.content.split(" ")[1]
    # Checks if word is an int, and of correct length, otherwise returns None
    try:
        int(test)
        if len(test) == 18:
            return test
        return None
    except ValueError:
        return None

async def userSearch(m):
    u = getID(m)
    if (u != None):
        sqlconn = sqlite3.connect('sdv.db')
        searchResults = sqlconn.execute("SELECT username, num, date, message, staff FROM badeggs WHERE id=?", [u]).fetchall()
        sqlconn.commit()
        sqlconn.close()

        if searchResults == []:
            await client.send_message(m.channel, "That user was not found in the database.")
        else:
            out = "That user was found with the following infractions:\n"
            for item in searchResults:
                if item[1] == 0:
                    out += "[{}] **{}** - Banned by {} - {}\n".format(formatTime(item[2]), item[0], item[4], item[3])
                else:
                    out += "[{}] **{}** - Warning #{} by {} - {}\n".format(formatTime(item[2]), item[0], item[1], item[4], item[3])
                if item[1] == warnThreshold:
                    out += "They have received {} warnings, it is recommended that they be banned.\n".format(warnThreshold)
            await client.send_message(m.channel, out)
    else:
        await client.send_message(m.channel, "Please mention only a single user that you wish to search")

async def logUser(m, ban):
    uid = getID(m)
    u = discord.utils.get(m.server.members, id=uid)
    if uid == None:
        await client.send_message(m.channel, "Please mention a user or provide a user ID `!warn/ban USERID message`")
        return # Still donno if this works

    sqlconn = sqlite3.connect('sdv.db')
    if (ban):
        count = 0
    else:
        count = sqlconn.execute("SELECT COUNT(*) FROM badeggs WHERE id=?", [uid]).fetchone()[0] + 1
    globalcount = sqlconn.execute("SELECT COUNT(*) FROM badeggs").fetchone()[0]
    currentTime = datetime.datetime.utcnow()
    if u == None and count > 1: # User not found in server, but found in database
        searchResults = sqlconn.execute("SELECT username FROM badeggs WHERE id=?", [uid]).fetchall()
        params = [globalcount + 1, uid, searchResults[0][0], count, currentTime, removeCommand(m.content), m.author.name]
    elif u != None: # User info is known
        params = [globalcount + 1, uid, "{}#{}".format(u.name, u.discriminator), count, currentTime, removeCommand(m.content), m.author.name]
    else: # User info is unknown
        params = [globalcount + 1, uid, "???", count, currentTime, removeCommand(m.content), m.author.name]
        await client.send_message(m.channel, "I wasn't able to find a username for that user, but whatever, I'll log them anyway.")

    sqlconn.execute("INSERT INTO badeggs (dbid, id, username, num, date, message, staff) VALUES (?, ?, ?, ?, ?, ?, ?)", params)
    sqlconn.commit()
    sqlconn.close()

    if ban:
        logMessage = "[{}] **{}** - Banned by {} - {}\n".format(formatTime(currentTime), params[2],  m.author.name, removeCommand(m.content))
    else:
        logMessage = "[{}] **{}** - Warning #{} by {} - {}\n".format(formatTime(currentTime), params[2], count, m.author.name, removeCommand(m.content))
    try:
        await client.send_message(client.get_channel(logChannel), logMessage)
    except discord.errors.InvalidArgument:
        await client.send_message(m.channel, "The logging channel has not been set up in `config.json`. In order to have a visual record, please specify a channel ID.")

    if (count >= warnThreshold and ban == False):
        logMessage += "This user has received {} warnings or more. It is recommened that they be banned.".format(warnThreshold)
    await client.send_message(m.channel, logMessage)
    try:
        if u != None:
            if ban and sendBanDM:
                mes = removeCommand(m.content)
                if mes != "":
                    await client.send_message(u[0], "You have been banned from the Stardew Valley server for the following reason: {}. If you have any questions, feel free to DM one of the staff members.".format(mes))
                else:
                    await client.send_message(u[0], "You have been banned from the Stardew Valley server for violating one of our rules. If you have any questions, feel free to DM one of the staff members.")
            elif ban == False and sendWarnDM:
                mes = removeCommand(m.content)
                if mes != "":
                    await client.send_message(u[0], "You have received Warning #{} in the Stardew Valley server for the following reason: {}. If you have any questions, feel free to DM one of the staff members.".format(count, mes))
                else:
                    await client.send_message(u[0], "You have received Warning #{} in the Stardew Valley server for violating one of our rules. If you have any questions, feel free to DM one of the staff members.".format(count))
    # I don't know if any of these are ever getting tripped
    except discord.errors.Forbidden:
        await client.send_message(message.channel, "ERROR: I am not allowed to DM the user. It is likely that they are not accepting DM's from me.")
    except discord.errors.HTTPException as e:
        await client.send_message(message.channel, "ERROR: While attempting to DM, there was an unexpected error. Tell aquova this: {}".format(e))
    except discord.errors.NotFound:
        await client.send_message(message.channel, "ERROR: I was unable to find the user to DM. I'm unsure how this can be the case, unless their account was deleted")

async def removeError(m):
    uid = getID(m)
    sqlconn = sqlite3.connect('sdv.db')
    searchResults = sqlconn.execute("SELECT dbid, username, num, date, message, staff FROM badeggs WHERE id=?", [uid]).fetchall()
    if searchResults == []:
        await client.send_message(m.channel, "That user was not found in the database.")
    else:
        item = searchResults[-1]
        sqlconn.execute("REPLACE INTO badeggs (dbid, id, username, num, date, message, staff) VALUES (?, NULL, NULL, NULL, NULL, NULL, NULL)", [item[0]])
        out = "The following log was deleted:\n"
        if item[2] == 0:
            out += "[{}] **{}** - Banned by {} - {}\n".format(formatTime(item[3]), item[1], item[5], item[4])
        else:
            out += "[{}] **{}** - Warning #{} by {} - {}\n".format(formatTime(item[3]), item[1], item[2], item[5], item[4])
        await client.send_message(m.channel, out)
    sqlconn.commit()
    sqlconn.close()

@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)

    game_object = discord.Game(name="type !help", type=0)
    await client.change_presence(game=game_object)

@client.event
async def on_message(message):
    if message.author.id != client.user.id:
        try:
            if message.channel.id in validInputChannels:
                if message.content.startswith("!search"):
                    if checkRoles(message.author):
                        await userSearch(message)
                elif message.content.startswith("!warn"):
                    if checkRoles(message.author):
                        await logUser(message, False)
                elif message.content.startswith("!ban"):
                    if checkRoles(message.author):
                        await logUser(message, True)
                elif message.content.startswith("!remove"):
                    if checkRoles(message.author):
                        await removeError(message)
                elif message.content.startswith('!help'):
                    helpMes = "Issue a warning: `!warn @USERNAME message`\nLog a ban: `!ban @USERNAME reason`\nSearch for a user: `!search @USERNAME`\nRemove a user's last log: `!remove @USERNAME`"
                    await client.send_message(message.channel, helpMes)
        except discord.errors.HTTPException:
            pass
        except Exception as e:
            await client.send_message(message.channel, "Something has gone wrong. Blame aquova, and tell him this: {}".format(e))

client.run(discordKey)
