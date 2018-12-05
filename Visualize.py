# Calculates statistics and generates plots

import sqlite3, math
import numpy as np
# Needed for OS X for some reason
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt

# The data here is data that I collected by hand myself prior to 8/30/18 (log #537 in the database)
# TODO: Add this data to a database table, then cache anytime the data is recomputed
# Dictionary is User -> [sum, bans, warns]
staffData = {
    "BattleShout": [39, 70],
    "Magically Clueless": [44, 62],
    "jev": [47, 27],
    "Zaph": [22, 44],
    "Golden": [26, 33],
    "Sweevle": [39, 19],
    "Alcopops": [41, 14],
    "FanDidlyTastic": [23, 18],
    "Lewis": [32, 2],
    "aquova": [19, 13],
    "Marmarru": [24, 4],
    "Danny": [8, 20],
    "Crumbledore": [2, 11],
    "eemie": [9, 2],
    "wut": [8, 1],
    "hweet": [8, 0],
    "Paulie": [7, 0],
    "Kim": [5, 0],
    "Pathoschild": [3, 2],
    "Spaztika": [2, 1],
    "Trias": [2, 1],
    "Kris": [2, 1],
    "pastelle": [2, 0],
    "Apollo": [2, 0],
    "Moiph": [0, 0],
    "Aero": [0, 0]
}

months = ["", "Jan", "Feb", "Mar", "Apr", "May", "June", "July", "Aug", "Sept", "Oct", "Nov", "Dec"]

# "MM-YYYY to [bans, warns]"
monthData = {
    "03-2016": [1, 0],
    "04-2016": [4, 0],
    "05-2016": [11, 0],
    "06-2016": [4, 0],
    "07-2016": [6, 0],
    "08-2016": [14, 0],
    "09-2016": [19, 1],
    "10-2016": [8, 3],
    "11-2016": [12, 6],
    "12-2016": [11, 3],
    "01-2017": [12, 3],
    "02-2017": [10, 8],
    "03-2017": [17, 10],
    "04-2017": [11, 2],
    "05-2017": [9, 6],
    "06-2017": [6, 1],
    "07-2017": [25, 7],
    "08-2017": [24, 3],
    "09-2017": [18, 4],
    "10-2017": [4, 3],
    "11-2017": [5, 3],
    "12-2017": [8, 9],
    "01-2018": [7, 9],
    "02-2018": [4, 11],
    "03-2018": [17, 18],
    "04-2018": [28, 24],
    "05-2018": [27, 55],
    "06-2018": [22, 42],
    "07-2018": [34, 59],
    "08-2018": [28, 68]
}

def roundup(x):
    return int(math.ceil(x / 10.0)) * 10 + 1

def getMax(a):
    maximum = 0
    for x in a:
        if (x[0] + x[1]) > maximum:
            maximum = x[0] + x[1]
    return roundup(maximum)

def genUserPlot():
    plt.clf()
    sqlconn = sqlite3.connect('sdv.db')
    data = sqlconn.execute("SELECT * FROM badeggs").fetchall()
    for log in data[538:]:
        if log[1] != None:
            username = log[6]
            if username not in staffData:
                staffData[username] = [0, 0]

            if log[3] == 0:
                staffData[username][0] += 1
            elif log[3] > 0:
                staffData[username][1] += 1
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
    plt.title("SDV Warns/Bans per User")
    plt.xticks(ind, sortedTotals)
    plt.xticks(rotation=-90)
    plt.yticks(np.arange(0, getMax(list(staffData.values())), 10))
    plt.legend((p1[0], p2[0]), ("Bans", "Warns"))
    plt.tight_layout()
    plt.grid(True, axis="y")

    # plt.show()
    plt.savefig("sdv_user_plot.png")

# A lot of code could be reused if I wanted to combine these functions
def genMonthlyPlot():
    plt.clf()
    sqlconn = sqlite3.connect("sdv.db")
    data = sqlconn.execute("SELECT * FROM badeggs").fetchall()
    for log in data[538:]:
        if log[1] != None:
            month = "{}-{}".format(log[4].split('-')[1], log[4].split('-')[0])
            if month not in monthData:
                monthData[month] = [0, 0]

            if log[3] == 0:
                monthData[month][0] += 1
            elif log[3] > 0:
                monthData[month][1] += 1
    sqlconn.close()

    bans = [monthData[x][0] for x in monthData]
    warns = [monthData[x][1] for x in monthData]
    labels = ["{} {}".format(months[int(x.split('-')[0])], x.split('-')[1]) for x in monthData.keys()]

    width = 0.5

    ind = np.arange(len(monthData.keys()))
    p1 = plt.bar(ind, bans, width, zorder=5)
    p2 = plt.bar(ind, warns, width, bottom=bans, zorder=5)
    plt.ylabel("Logs")
    plt.xlabel("Month")
    plt.title("SDV Warns/Bans per Month")
    plt.xticks(ind, labels)
    plt.xticks(rotation=-90)
    plt.yticks(np.arange(0, getMax(list(monthData.values())), 10))
    plt.legend((p1[0], p2[0]), ("Bans", "Warns"))
    plt.tight_layout()
    plt.grid(True, axis="y")

    # plt.show()
    plt.savefig("sdv_month_plot.png")

# if __name__ == "__main__":
#     genUserPlot()
#     genMonthlyPlot()
