# Calculates statistics and generates plots

import math, os, discord
import numpy as np
# Needed for OS X for some reason
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import db
from config import USER_PLOT, MONTH_PLOT

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
def updateCache(staff, val, date):
    formatDate = f"{date.split('-')[0]}-{date.split('-')[1]}"

    checkStaff = db.get_staffdata(staff)
    checkDate = db.get_monthdata(formatDate)

    # First time user has posted
    if checkStaff == []:
        db.add_staffdata(staff, val[0], val[1], False)
    else:
        bans = checkStaff[0][1]
        warns = checkStaff[0][2]
        if (bans + val[0] < 0) or (warns + val[1] < 0):
            print("Hey, a user is going to have a negative balance, that's no good.")
        db.add_staffdata(staff, bans + val[0], warns + val[1], True)

    # First log this month
    if checkDate == []:
        db.add_monthdata(formatDate, val[0], val[1], False)
    else:
        bans = checkDate[0][1]
        warns = checkDate[0][2]
        if (bans + val[0] < 0) or (warns + val[1] < 0):
            print("Hey, a user is going to have a negative balance, that's no good.")
        db.add_monthdata(formatDate, bans + val[0], warns + val[1], True)

def gen_user_plot():
    plt.clf()
    data = db.get_staffdata(None)
    staffData = {x[0]: [x[1], x[2]] for x in data}

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
    plt.yticks(np.arange(0, getMax(list(staffData.values())), 20))
    plt.legend((p1[0], p2[0]), ("Bans", "Warns"))
    plt.tight_layout()
    plt.grid(True, axis="y")

    plt.savefig(USER_PLOT)

def gen_monthly_plot():
    plt.clf()
    plt.figure(figsize=(10,6))
    data = db.get_monthdata(None)
    sortedData = sorted(data)
    monthData = {x[0]: [x[1], x[2]] for x in sortedData}

    bans = [monthData[x][0] for x in monthData]
    warns = [monthData[x][1] for x in monthData]
    labels = [f"{months[int(x.split('-')[1])]} {x.split('-')[0]}" for x in monthData.keys()]

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

    plt.savefig(MONTH_PLOT)

async def post_plots(message, _):
    gen_user_plot()
    gen_monthly_plot()

    with open(USER_PLOT, 'rb') as f:
        await message.channel.send(file=discord.File(f))

    with open(MONTH_PLOT, 'rb') as f:
        await message.channel.send(file=discord.File(f))
