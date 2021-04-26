import discord, re
import db, utils

class UserLookup:
    def __init__(self):
        self.recent_bans = {}

    def add_ban(self, userid, username):
        self.recent_bans[userid] = username

    # Attempts to return a user ID
    def parse_mention(self, message):
        # Users can be mentioned one of three ways:
        # - By pinging them
        # - By their username
        # - By their ID

        user_id = None
        user_id = self.check_mention(message)

        if user_id == None:
            user_id = self.check_username(message)

        if user_id == None:
            user_id = self.check_id(message)

        return user_id

    def check_mention(self, message):
        try:
            return message.mentions[0].id
        except IndexError:
            return None

    def check_username(self, message):
        # Usernames can have spaces, so need to throw away the first word (the command),
        # and then everything after the discriminator
        testUsername = utils.strip_words(message.content, 1)

        try:
            # Some people *coughs* like to put a '@' at beginning of the username.
            # Remove the '@' if it exists at the front of the message
            if testUsername[0] == "@":
                testUsername = testUsername[1:]

            # Parse out the actual username
            user = testUsername.split("#")
            discriminator = user[1].split()[0]
            userFound = discord.utils.get(message.guild.members, name=user[0], discriminator=discriminator)
            if userFound != None:
                return userFound.id

            # If not found in server, check if they're in the recently banned dict
            fullname = f"{user[0]}#{discriminator}"
            if fullname in list(self.recent_bans.values()):
                revBans = {v: k for k, v in self.recent_bans.items()}
                return revBans[fullname]

            # If they still haven't been found, check database
            return db.fetch_id_by_username(fullname)
        except IndexError:
            return None

    def check_id(self, message):
        content = utils.strip_words(message.content, 1)

        try:
            # If ping is typed out by user using their ID, it doesn't count as a mention
            # Thus, try and match with regex
            checkPing = re.search(r"<@!?(\d+)>", content)
            if checkPing != None:
                return int(checkPing.group(1))

            # Simply verify by attempting to cast to an int. If it doesn't raise an error, return it
            # NOTE: This requires the ID to be first word, after the command
            checkID = content.split()[0]
            return int(checkID)
        except (IndexError, ValueError):
            return None

    def fetch_username(self, server, userid):
        username = None

        member = self.fetch_user(server, userid)
        if member != None:
            # If we found a member in the server, simply format the username
            username = f"{member.name}#{member.discriminator}"

        if username == None:
            # If user has recently left, use that username
            if userid in self.recent_bans:
                username = self.recent_bans[userid]

        if username == None:
            # Check the database to see if we can get their name from their most recent infraction (if any)
            checkDatabase = db.search(userid)
            if checkDatabase != []:
                username = checkDatabase[-1].name

        return username

    def fetch_user(self, server, userid):
        return discord.utils.get(server.members, id=userid)
