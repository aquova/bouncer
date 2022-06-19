# Calculates statistics and generates plots
import math

import discord
import numpy as np
import matplotlib.pyplot as plt

from config import USER_PLOT, MONTH_PLOT
import db

months = ["", "Jan", "Feb", "Mar", "Apr", "May", "June", "July", "Aug", "Sept", "Oct", "Nov", "Dec"]

def roundup(val: float) -> int:
    return int(math.ceil(val / 10.0)) * 10 + 1

def get_max(arr: list[tuple[int, int]]) -> int:
    maximum = 0
    for val in arr:
        if (val[0] + val[1]) > maximum:
            maximum = val[0] + val[1]
    return roundup(maximum)

# Val is a tuple which determines what to modify
# (ban # change, warn # change)
def update_cache(staff: str, val: tuple[int, int], date: str):
    format_date = f"{date.split('-')[0]}-{date.split('-')[1]}"

    check_staff = db.get_staffdata(staff)
    check_date = db.get_monthdata(format_date)

    # First time user has posted
    if not check_staff:
        db.add_staffdata(staff, val[0], val[1], False)
    else:
        bans = check_staff[0][1]
        warns = check_staff[0][2]
        if (bans + val[0] < 0) or (warns + val[1] < 0):
            print("Hey, a user is going to have a negative balance, that's no good.")
        db.add_staffdata(staff, bans + val[0], warns + val[1], True)

    # First log this month
    if not check_date:
        db.add_monthdata(format_date, val[0], val[1], False)
    else:
        bans = check_date[0][1]
        warns = check_date[0][2]
        if (bans + val[0] < 0) or (warns + val[1] < 0):
            print("Hey, a user is going to have a negative balance, that's no good.")
        db.add_monthdata(format_date, bans + val[0], warns + val[1], True)

def gen_user_plot():
    plt.clf()
    data = db.get_staffdata(None)
    staff_data = {x[0]: [x[1], x[2]] for x in data}

    staff_totals = {k: v[0]+v[1] for k, v in staff_data.items()}
    sorted_totals = sorted(staff_totals, key=staff_totals.get)[::-1]

    bans = [staff_data[x][0] for x in sorted_totals]
    warns = [staff_data[x][1] for x in sorted_totals]
    width = 0.5

    ind = np.arange(len(staff_data.keys()))
    plot1 = plt.bar(ind, bans, width, zorder=5)
    plot2 = plt.bar(ind, warns, width, bottom=bans, zorder=5)
    plt.ylabel("Logs")
    plt.xlabel("User")
    plt.title("Warns/Bans per User")
    plt.xticks(ind, sorted_totals)
    plt.xticks(rotation=-90)
    plt.yticks(np.arange(0, get_max(list(staff_data.values())), 20))
    plt.legend((plot1[0], plot2[0]), ("Bans", "Warns"))
    plt.tight_layout()
    plt.grid(True, axis="y")

    plt.savefig(USER_PLOT)

def gen_monthly_plot():
    plt.clf()
    plt.figure(figsize=(10,6))
    data = db.get_monthdata(None)
    sorted_data = sorted(data)
    month_data = {x[0]: [x[1], x[2]] for x in sorted_data}

    bans = [month_data[x][0] for x in month_data]
    warns = [month_data[x][1] for x in month_data]
    labels = [f"{months[int(x.split('-')[1])]} {x.split('-')[0]}" for x in month_data.keys()]

    width = 0.5

    ind = np.arange(len(month_data.keys()))
    plot1 = plt.bar(ind, bans, width, zorder=5)
    plot2 = plt.bar(ind, warns, width, bottom=bans, zorder=5)
    plt.ylabel("Logs")
    plt.xlabel("Month")
    plt.title("Warns/Bans per Month")
    plt.xticks(ind, labels)
    plt.xticks(rotation=-90)
    plt.yticks(np.arange(0, get_max(list(month_data.values())), 10))
    plt.legend((plot1[0], plot2[0]), ("Bans", "Warns"))
    plt.tight_layout()
    plt.grid(True, axis="y")

    plt.savefig(MONTH_PLOT)

async def post_plots(message: discord.Message, _):
    gen_user_plot()
    gen_monthly_plot()

    with open(USER_PLOT, 'rb') as user_file:
        await message.channel.send(file=discord.File(user_file))

    with open(MONTH_PLOT, 'rb') as month_file:
        await message.channel.send(file=discord.File(month_file))
