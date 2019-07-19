# Bot functionality to do Zaph's job for him
import discord, sqlite3
from Utils import DATABASE_PATH

class Hunter:
    def __init__(self):
        self.watchedChannel = None
        self.hunters = set()

    def getWatchedChannel(self):
        return self.watchedChannel.id

    # Sets the channel object to watch for reactions
    def setWatchedChannel(self, channel):
        self.watchedChannel = channel

    # Resets to watch no channel, updates DB
    def stopWatching(self):
        sqlconn = sqlite3.connect(DATABASE_PATH)
        for user in self.hunters:
            count = sqlconn.execute("SELECT COUNT(*) FROM hunters WHERE id=?", [user.id]).fetchone()[0] + 1
            params = [user.id, "{}#{}".format(user.name, user.discriminator), count]
            sqlconn.execute("REPLACE INTO hunters (id, username, count) VALUES (?, ?, ?)", params)

        sqlconn.commit()
        sqlconn.close()
        self.watchedChannel = None
        self.hunters.clear()

    # Add user to set
    def addReaction(self, user):
        self.hunters.add(user)
