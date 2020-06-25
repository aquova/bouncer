import db
from user import UserLookup

class Watcher:
    def __init__(self):
        self.watchlist = [x[0] for x in db.get_watch_list()]
        self.ul = UserLookup()

    def should_note(self, id):
        return id in self.watchlist

    def remove_user(self, id):
        if id in self.watchlist:
            db.del_watch(id)
            self.watchlist.remove(id)

    async def watch_user(self, mes, _):
        userid = self.ul.parse_mention(mes)
        if userid == None:
            await mes.channel.send("I was unable to find a user in that message")
            return

        db.add_watch(userid)
        self.watchlist.append(userid)

        username = self.ul.fetch_username(mes.guild, userid)
        await mes.channel.send(f"{username} has been added to the watch list. :spy:")

    async def unwatch_user(self, mes, _):
        userid = self.ul.parse_mention(mes)
        if userid == None:
            await mes.channel.send("I was unable to find a user in that message")
            return
        elif userid not in self.watchlist:
            await mes.channel.send("...That user is not being watched")
            return

        self.remove_user(userid)

        username = self.ul.fetch_username(mes.guild, userid)
        await mes.channel.send(f"{username} has been removed from the watch list.")

    async def get_watchlist(self, mes, _):
        if len(self.watchlist) == 0:
            await mes.channel.send("There are no users being watched")
            return

        output = "```"
        for userid in self.watchlist:
            username = self.ul.fetch_username(mes.guild, userid)
            output += f"{username} "
        output += "```"

        await mes.channel.send(output)
