"""
A Discord moderation bot, originally made for the Stardew Valley server
Written by aquova, 2018
"""

import discord, json, asyncio, sqlite3, datetime

with open('config.json') as config_file:
    cfg = json.load(config_file)

discordKey = str(cfg['discord'])
validInputChannels = cfg['channels']['listening']
logChannel = str(cfg['channels']['log'])

client = discord.Client()

# Create needed database, if doesn't exist
sqlconn = sqlite3.connect('sdv.db')
sqlconn.execute("CREATE TABLE IF NOT EXISTS badeggs (id INT PRIMARY KEY, username TEXT, num INT, date DATE, message TEXT, staff TEXT);")
sqlconn.commit()
sqlconn.close()

def removeCommand(m):
    tmp = m.split(" ")[2:]
    return " ".join(tmp)

async def userSearch(u, m):
    if (len(u) == 1):
        sqlconn = sqlite3.connect('sdv.db')
        searchResults = sqlconn.execute("SELECT username, num, date, message, staff FROM badeggs WHERE id=?", [u[0].id]).fetchall()
        sqlconn.commit()
        sqlconn.close()

        if searchResults == []:
            await client.send_message(m.channel, "That user was not found in the database.")
        else:
            out = "That user was found with the following infractions:\n"
            for item in searchResults:
                if item[1] == 0:
                    out += "{} was banned on {} by {} for this reason: {}\n".format(item[0], item[2], item[4], item[3])
                else:
                    out += "{} was received Warning {} on {} by {} for this reason: {}\n".format(item[0], item[1], item[2], item[4], item[3])
                if item[1] == 3:
                    out += "They have received 3 warning, it is recommended that they be banned.\n"
            await client.send_message(m.channel, out)
    else:
        await client.send_message(m.channel, "Please mention only a single user that you wish to search")

@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)

@client.event
async def on_message(message):
    if message.author.id != client.user.id:
        try:
            if message.channel.id in validInputChannels:
                if message.content.startswith("!search"):
                    user = message.mentions
                    await userSearch(user, message)
                elif message.content.startswith("!warned"):
                    user = message.mentions
                    if len(user) == 1:
                        sqlconn = sqlite3.connect('sdv.db')
                        # TODO: This could potentially be a problem if you try to warn again after banning
                        count = sqlconn.execute("SELECT COUNT(*) FROM badeggs").fetchone()[0]
                        currentTime = datetime.datetime.utcnow()
                        params = [user[0].id, user[0].name, count + 1, currentTime, removeCommand(message.content), message.author.name]
                        sqlconn.execute("INSERT INTO badeggs (id, username, num, date, message, staff) VALUES (?, ?, ?, ?, ?, ?)", params)
                        sqlconn.commit()
                        sqlconn.close()
                        await client.send_message(message.channel, "User was warned.")
                        # userSearch(user, message)
                    print("Warned user")
                elif message.content.startswith("!banned"):
                    print("Banned User")
            else:
                print("Invalid channel")

        except discord.errors.HTTPException:
            pass

client.run(discordKey)
