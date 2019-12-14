import discord, sqlite3, re
import Utils
from Utils import DATABASE_PATH

"""
User Class

A class that, given a Discord message, will attempt to identify the corresponding User
"""
class User:
    """
    Custom Error, thrown when message couldn't be parsed to find a user
    """
    class MessageError(Exception):
        pass

    """
    Initialization

    Inputs:
        message: Discord message object
        banList: Dictionary of users who have been banned/left the server since startup
    """
    def __init__(self, message, banList):
        self.message = message
        self.id = self.getID(banList)

    """
    Get ID

    Attempts to get the Discord user ID for the user mentioned in the message

    Input:
        banList: Dictionary of users who have been banned/left the server since startup
    """
    def getID(self, banList):
        # Users can be mentioned one of three ways:
        # - Simply by their ID
        # - Simply by their username
        # - By pinging them

        # Check if any user was pinged in the message
        if len(self.message.mentions) > 0:
            # The pinging should take place as the first word of the message (in case users want to ping someone else in the log body)
            possibleID = self.message.mentions[0].id
            # Discord pings are of the form '<@ID>' or '<@!ID>'. Need to check for both
            # TODO: Change this to match regex pattern below
            if (self.message.content.split(" ")[1] == "<@{}>".format(possibleID) or (self.message.content.split(" ")[1] == "<@!{}>".format(possibleID))):
                return possibleID

        # Check if the username was provided
        checkUsername = Utils.parseUsername(self.message, banList)
        if checkUsername != None:
            return checkUsername

        # Check if it is an ID
        checkID = self.message.content.split(" ")[1]

        # If ping is typed out by user using their ID, it doesn't count as a mention
        # Thus, try and match with regex
        checkPing = re.search(r"<@!?(\d+)>", checkID)
        if checkPing != None:
            return checkPing.group(1)

        # Finally, see if it's just an ID
        try:
            # Simply verify by attempting to cast to an int. If it doesn't raise an error, return it
            # Lengths of Discord IDs seem to be no longer a constant length, so difficult to verify that way
            int(checkID)
            return checkID
        except ValueError:
            raise self.MessageError("Couldn't understand message.")

    """
    Get Member

    Attempts to identify a Discord member object from self.id
    """
    def getMember(self):
        # Iterate through all Discord members, check if IDs are the same
        # TODO: May want to throw error if self.id is invalid
        u = [x for x in self.message.guild.members if x.id == int(self.id)]

        # ID's are unique, so can simply return the first match (if there is one)
        if len(u) == 0:
            return None
        else:
            return u[0]

    """
    Get Name

    Attempts to get the user's name from their Discord User object

    Inputs:
        banList: Dictionary of users who have been banned/left the server since startup
    """
    def getName(self, banList):
        member = self.getMember()
        # If we found a member, simply format the username and return
        if member != None:
            return "{}#{}".format(member.name, member.discriminator)

        # If their ID was found in the ban list, it's already formatted properly, so return it
        if self.id in banList:
            return banList[self.id]

        # Otherwise, they aren't in the server, and haven't left since startup.
        # Check the database to see if we can get their name from a previous infraction
        checkDatabase = self.search()
        if checkDatabase == []:
            raise self.MessageError("User not found")
        return checkDatabase[-1][2]

    """
    Search

    Attempt to search the database for a user with ID of self.id
    """
    def search(self):
        sqlconn = sqlite3.connect(DATABASE_PATH)
        searchResults = sqlconn.execute("SELECT dbid, id, username, num, date, message, staff, post FROM badeggs WHERE id=?", [self.id]).fetchall()
        sqlconn.commit()
        sqlconn.close()

        return searchResults
