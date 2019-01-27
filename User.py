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
        # First check if they're mentioned
        if len(self.message.mentions) > 0:
            # Need to make sure pinged user is in the right position
            possibleUsername = self.message.mentions[0].id
            if (self.message.content.split(" ")[1] == "<@{}>".format(possibleUsername) or (self.message.content.split(" ")[1] == "<@!{}>".format(possibleUsername))):
                return possibleUsername

        # Then check if username is valid
        checkUsername = Utils.parseUsername(self.message, banList)
        if checkUsername != None:
            return checkUsername
        checkID = self.message.content.split(" ")[1]

        # Finally, check if it is an ID
        try:
            int(checkID)
            return checkID
        except ValueError:
            raise self.MessageError("Couldn't understand message.")

    def getMember(self):
        return discord.utils.get(self.message.server.members, id=self.id)

    def getName(self, banList):
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
