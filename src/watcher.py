import discord

import db
from client import client
from commonbot.user import UserLookup
from utils import get_userid


class Watcher:
    def __init__(self):
        self.watchlist = [x[0] for x in db.get_watch_list()]
        self.ul = UserLookup()

    def should_note(self, id: int) -> bool:
        return id in self.watchlist

    def remove_user(self, id: int):
        if id in self.watchlist:
            db.del_watch(id)
            self.watchlist.remove(id)

    async def watch_user(self, mes: discord.Message, _):
        userid, _ = await get_userid(self.ul, mes, "watch")
        if not userid:
            return

        db.add_watch(userid)
        self.watchlist.append(userid)

        username = self.ul.fetch_username(client, userid)
        await mes.channel.send(f"{username} has been added to the watch list. :spy:")

    async def unwatch_user(self, mes: discord.Message, _):
        userid, _ = await get_userid(self.ul, mes, "unwatch")
        if not userid:
            return
        elif userid not in self.watchlist:
            await mes.channel.send("...That user is not being watched")
            return

        self.remove_user(userid)

        username = self.ul.fetch_username(client, userid)
        await mes.channel.send(f"{username} has been removed from the watch list.")

    async def get_watchlist(self, mes: discord.Message, _):
        if len(self.watchlist) == 0:
            await mes.channel.send("There are no users being watched")
            return

        output = "```"
        for userid in self.watchlist:
            username = self.ul.fetch_username(client, userid)
            if username:
                output += f"{username} ({userid})\n"
            else:
                # If we couldn't find them, just prune them
                self.remove_user(userid)

        output += "```"

        await mes.channel.send(output)
