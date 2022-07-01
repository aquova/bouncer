import discord

class DiscordClient(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)

my_intents = discord.Intents.all()
client = DiscordClient(intents=my_intents)
