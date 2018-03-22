"""
A Discord moderation bot, originally made for the Stardew Valley server
Written by aquova, 2018
"""

import discord, json, asyncio, sqlite3

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
    tmp = m.split(" ")[1:]
    return " ".join(tmp)

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
                    if (len(user) == 1):
                        sqlconn = sqlite3.connect('sdv.db')
                        searchResults = sqlconn.execute("SELECT username, num, message FROM badeggs WHERE id=?", [user[0].id]).fetchall()
                        sqlconn.commit()
                        sqlconn.close()

                        if searchResults == []:
                            await client.send_message(message.channel, "That user was not found in the database.")
                        else:
                            out = "That user was found with the following infractions:\n"
                            for item in searchResults:
                                if item[1] == 0:
                                    out += "{} was banned on {} by {} for this reason: {}\n".format(item[0], item[2], item[4], item[3])
                                else:
                                    out += "{} was received warning {} on {} by {} for this reason: {}\n".format(item[0], item[1], item[2], item[4], item[3])
                                if item[1] == 3:
                                    out += "They have received 3 warning, it is recommended that they be banned.\n"
                            await client.send_message(message.channel, out)
                    else:
                        await client.send_message(message.channel, "Please mention only a single user, which you wish to search")
                elif message.content.startswith("!warned"):
                    print("Warned user")
                elif message.content.startswith("!banned"):
                    print("Banned User")
            else:
                print("Invalid channel")

        except discord.errors.HTTPException:
            pass

client.run(discordKey)
