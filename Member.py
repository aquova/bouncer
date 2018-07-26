import discord, sqlite3
import Utils

class User:
    class MessageError(Exception):
        pass

    def __init__(self, message, banList):
        self.message = message
        self.id = self.getID(banList)

    # Gets the ID from a message
    def getID(self, banList):
        if len(self.message.mentions) == 1:
            return self.message.mentions[0].id
        checkID = self.message.content.split(" ")[1]
        try:
            int(checkID)
            return checkID
        except ValueError:
            checkUsername = Utils.parseUsername(self.message, banList)
            if checkUsername != None:
                return checkUsername
            raise self.MessageError("Couldn't understand message.")

    def getMember(self):
        return discord.utils.get(self.message.server.members, id=self.id)

    def getName(self):
        member = self.getMember()
        if member != None:
            return "{}#{}".format(member.name, member.discriminator)
        if self.id in banList:
            return banList[self.id]
        checkDatabase = self.search()
        if checkDatabase == []:
            raise self.MessageError("User not found")
        return checkDatabase[-1][0]

    def search(self):
        sqlconn = sqlite3.connect('sdv.db')
        searchResults = sqlconn.execute("SELECT username, num, date, message, staff FROM badeggs WHERE id=?", [self.id]).fetchall()
        sqlconn.commit()
        sqlconn.close()

        return searchResults
