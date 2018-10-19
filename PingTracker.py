# Functions to keep track of any unresponded DMs to Bouncer
# aquova, 2018

import discord, sqlite3, datetime
import Utils

def unresolved():
    output = ""
    sqlconn = sqlite3.connect('sdv.db')
    unresolved = sqlconn.execute("SELECT * FROM pings WHERE resolved = 0").fetchall()
    sqlconn.close()

    if unresolved == []:
        return "There are no unresolved pings."

    for m in unresolved:
        time = m[4].split(".")[0]
        f = "**{}** (ID: {}) messaged me @ {}: {}".format(m[2], m[1], time, m[3])
        output += f + '\n'

    return output

def newPing(message):
    sqlconn = sqlite3.connect('sdv.db')
    dbnum = sqlconn.execute("SELECT COUNT(*) FROM pings").fetchone()[0]
    uname = "{}#{}".format(message.author.name, message.author.discriminator)

    # If their most recent ping was less than 15 minutes ago, consider this part of the same issue
    # pingsFromUser = sqlconn.execute("SELECT * FROM pings WHERE userid = ?", (message.author.id,)).fetchall()
    # if pingsFromUser != []:
    #     lastTime = pingsFromUser[-1][3]

    currTime = datetime.datetime.utcnow()
    params = [dbnum, message.author.id, uname, message.content, currTime]
    sqlconn.execute("INSERT INTO pings (dbid, userid, username, message, mesTime, respTime, resolved) VALUES (?, ?, ?, ?, ?, NULL, 0)", params)
    sqlconn.commit()
    sqlconn.close()

def resolvePing(userid):
    sqlconn = sqlite3.connect("sdv.db")
    pingsFromUser = sqlconn.execute("SELECT * FROM pings WHERE userid = ?", (userid,)).fetchall()
    if pingsFromUser != []:
        lastPing = pingsFromUser[-1]
        currTime = datetime.datetime.utcnow()
        # Replace respTime with the current time, and set resolved to true
        # There's probably a way to transplant the first 5 values slicker, but whatever
        params = [lastPing[0], lastPing[1], lastPing[2], lastPing[3], lastPing[4], currTime, 1]
        sqlconn.execute("REPLACE INTO pings (dbid, userid, username, message, mesTime, respTime, resolved) VALUES (?, ?, ?, ?, ?, ?, ?)", params)
    sqlconn.commit()
    sqlconn.close()
