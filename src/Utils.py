# Utility functions for bouncer

import discord, time, sqlite3
from config import DATABASE_PATH, LogTypes

# Removes the first word of a string
def strip(m):
    tmp = m.split()[1:]
    return " ".join(tmp)

def get_command(m):
    try:
        return m.split()[0]
    except IndexError:
        return ""

# Removes the '$command' to get just the request
def removeCommand(m):
    tmp = m.split()[2:]
    return " ".join(tmp)

def formatTime(t):
    # Input t is of the form: YYYY-MM-DD HH:MM:SS.SSSSSS
    date = str(t).split()[0]
    # output is of the form YYYY-MM-DD
    return date

# Checks if given user has one of the roles specified in config.json
def checkRoles(user, validRoles):
    try:
        if len(validRoles) == 1 and validRoles[0] == "":
            return True
        for role in user.roles:
            for r in validRoles:
                if role.id == r:
                    return True
        return False
    except AttributeError as e:
        print("The user {}#{} had this issue {}".format(user.name, user.discriminator, e))

# Since usernames can have spaces, first check if it's a username, otherwise just cut off first word as normal
# 'user' will either be the correct username, or an ID.
def parseMessage(message, username):
    m = " ".join(message.split()[1:])
    if m.startswith(username):
        return m[len(username)+1:]
    return removeCommand(message)

def getTimeDelta(t1, t2):
    # t1 should be larger than t2
    delta = t1 - t2
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return delta.days, hours, minutes

# Combines message content and attachment URLs together
def combineMessage(mes):
    out = mes.content
    if mes.attachments != []:
        for item in mes.attachments:
            out += '\n' + item.url

    return out

def get_mes_link(mes):
    return "https://discordapp.com/channels/{}/{}/{}".format(mes.guild.id, mes.channel.id, mes.id)
