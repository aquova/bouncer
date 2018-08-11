# Utility functions for bouncer

import discord, time, sqlite3

# Removes the '$command' to get just the request
def removeCommand(m):
    tmp = m.split(" ")[2:]
    return " ".join(tmp)

# Formats a datetime object to be European-style time string
def formatTime(t):
    # Input t is of the form: YYYY-MM-DD HH:MM:SS.SSSSSS
    date = str(t).split(" ")[0]
    pieces = date.split("-")
    # output is of the form DD/MM/YYYY
    european = "{}/{}/{}".format(pieces[2], pieces[1], pieces[0])
    return european

# Checks if given user has one of the roles specified in config.json
def checkRoles(user, validRoles):
    if len(validRoles) == 1 and validRoles[0] == "":
        return True
    for role in user.roles:
        for r in validRoles:
            if role.id == r:
                return True
    return False

# Parses the message to check if there's a valid username, then attempts to find their ID
def parseUsername(message, recentBans):
    # Usernames can have spaces, so need to throw away the first word (the command),
    # and then everything after the discriminator

    # Remove command
    testUsername = message.content.split(" ")[1:]
    testUsername = " ".join(testUsername)
    # Remove a "@" if it exists at the front of the message
    if testUsername[0] == "@":
        testUsername = testUsername[1:]

    try:
        # Parse out the actual username
        user = testUsername.split("#")
        discriminator = user[1].split(" ")
        user = "{}#{}".format(user[0], discriminator[0])

        userFound = discord.utils.get(message.server.members, name=user.split("#")[0], discriminator=user.split("#")[1])
        if userFound != None:
            return userFound.id

        if user in list(recentBans.values()):
            revBans = {v: k for k, v in recentBans.items()}
            return revBans[user]

        sqlconn = sqlite3.connect('sdv.db')
        searchResults = sqlconn.execute("SELECT id FROM badeggs WHERE username=?", [user]).fetchall()
        sqlconn.close()
        if searchResults != []:
            return searchResults[0][0]
        else:
            return None
    except IndexError:
        return None

#########################################################
# Functions that only need to be called once in a while #
#########################################################

# Exports the user list to a .txt file
def fetchUserList():
    with open("users.txt", 'w') as f:
        mems = message.server.members
        for u in mems:
            f.write("{}\n".format(u.name))

# Fetches a dict of the role names to ID values for the given server
# serverID needs to be a string
def fetchRoleList(serverID):
    s = client.get_server(serverID)
    roles = {role.name: role.id for role in s.roles}
    for r in roles:
        print("{} : {}".format(r, roles[r]))

def dumpBans(banList):
    output = ""
    for user in list(banList.items()):
        output += "{}: {}\n".format(user, banList[user])
    return output
