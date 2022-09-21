import discord

class DiscordClient(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = discord.app_commands.CommandTree(self)

    async def sync_guild(self, guild: discord.Guild):
        import context
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

my_intents = discord.Intents.all()
client = DiscordClient(intents=my_intents)
