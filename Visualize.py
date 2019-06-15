# Calculates statistics and generates plots

import sqlite3, math
import numpy as np
# Needed for OS X for some reason
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from Utils import DATABASE_PATH

months = ["", "Jan", "Feb", "Mar", "Apr", "May", "June", "July", "Aug", "Sept", "Oct", "Nov", "Dec"]

def roundup(x):
    return int(math.ceil(x / 10.0)) * 10 + 1

def getMax(a):
    maximum = 0
    for x in a:
        if (x[0] + x[1]) > maximum:
            maximum = x[0] + x[1]
    return roundup(maximum)

# Val is a tuple which determines what to modify
# (ban # change, warn # change)
def updateCache(sqlconn, staff, val, date):
    formatDate = "{}-{}".format(date.split('-')[0], date.split('-')[1])

    checkStaff = sqlconn.execute("SELECT * FROM staffLogs WHERE staff=?", [staff]).fetchall()
    checkDate = sqlconn.execute("SELECT * FROM monthLogs WHERE month=?", [formatDate]).fetchall()

    # First time user has posted
    if checkStaff == []:
        sqlconn.execute("INSERT INTO staffLogs (staff, bans, warns) VALUES (?, ?, ?)", [staff, val[0], val[1]])
    else:
        bans = checkStaff[0][1]
        warns = checkStaff[0][2]
        if (bans + val[0] < 0) or (warns + val[1] < 0):
            print("Hey, a user is going to have a negative balance, that's no good.")
        sqlconn.execute("REPLACE INTO staffLogs (staff, bans, warns) VALUES (?, ?, ?)", [staff, bans+val[0], warns+val[1]])

    # First log this month
    if checkDate == []:
        sqlconn.execute("INSERT INTO monthLogs (month, bans, warns) VALUES (?, ?, ?)", [formatDate, val[0], val[1]])
    else:
        bans = checkDate[0][1]
        warns = checkDate[0][2]
        if (bans + val[0] < 0) or (warns + val[1] < 0):
            print("Hey, a user is going to have a negative balance, that's no good.")
        sqlconn.execute("REPLACE INTO monthLogs (month, bans, warns) VALUES (?, ?, ?)", [formatDate, bans+val[0], warns+val[1]])

    sqlconn.commit()

def genUserPlot():
    plt.clf()
    sqlconn = sqlite3.connect(DATABASE_PATH)
    data = sqlconn.execute("SELECT * FROM staffLogs").fetchall()
    staffData = {x[0]: [x[1], x[2]] for x in data}
    sqlconn.close()

    staffTotals = {k: v[0]+v[1] for k, v in staffData.items()}
    sortedTotals = sorted(staffTotals, key=staffTotals.get)[::-1]

    bans = [staffData[x][0] for x in sortedTotals]
    warns = [staffData[x][1] for x in sortedTotals]
    width = 0.5

    ind = np.arange(len(staffData.keys()))
    p1 = plt.bar(ind, bans, width, zorder=5)
    p2 = plt.bar(ind, warns, width, bottom=bans, zorder=5)
    plt.ylabel("Logs")
    plt.xlabel("User")
    plt.title("Warns/Bans per User")
    plt.xticks(ind, sortedTotals)
    plt.xticks(rotation=-90)
    plt.yticks(np.arange(0, getMax(list(staffData.values())), 10))
    plt.legend((p1[0], p2[0]), ("Bans", "Warns"))
    plt.tight_layout()
    plt.grid(True, axis="y")

    plt.savefig("private/user_plot.png")

# A lot of code could be reused if I wanted to combine these functions
def genMonthlyPlot():
    plt.clf()
    sqlconn = sqlite3.connect(DATABASE_PATH)
    data = sqlconn.execute("SELECT * FROM monthLogs").fetchall()
    sortedData = sorted(data)
    monthData = {x[0]: [x[1], x[2]] for x in sortedData}
    sqlconn.close()

    bans = [monthData[x][0] for x in monthData]
    warns = [monthData[x][1] for x in monthData]
    labels = ["{} {}".format(months[int(x.split('-')[1])], x.split('-')[0]) for x in monthData.keys()]

    width = 0.5

    ind = np.arange(len(monthData.keys()))
    p1 = plt.bar(ind, bans, width, zorder=5)
    p2 = plt.bar(ind, warns, width, bottom=bans, zorder=5)
    plt.ylabel("Logs")
    plt.xlabel("Month")
    plt.title("Warns/Bans per Month")
    plt.xticks(ind, labels)
    plt.xticks(rotation=-90)
    plt.yticks(np.arange(0, getMax(list(monthData.values())), 10))
    plt.legend((p1[0], p2[0]), ("Bans", "Warns"))
    plt.tight_layout()
    plt.grid(True, axis="y")

    plt.savefig("private/month_plot.png")
