import discord

import db

class Watcher:
    def __init__(self):
        self.watchlist = db.get_watch_list()

    def should_note(self, uid: int) -> bool:
        return uid in self.watchlist

    def remove_user(self, uid: int):
        if uid in self.watchlist:
            db.del_watch(uid)
            self.watchlist.remove(uid)

    def handle_watch(self, user: discord.User, watch: bool) -> str:
        if watch:
            db.add_watch(user.id)
            self.watchlist.append(user.id)
            return f"{str(user)} has been added to the watch list. :spy:"
        else:
            if user.id not in self.watchlist:
                return "...That user is not being watched"
            self.remove_user(user.id)
            return f"{str(user)} has been removed from the watch list."

    def get_watchlist(self) -> str:
        if len(self.watchlist) == 0:
            return "There are no users being watched"
        return "\n".join([f"<@{x}>" for x in self.watchlist])
