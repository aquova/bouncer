import discord
from client import client
import commands

@client.tree.context_menu(name="Search")
async def search_context(interaction: discord.Interaction, user: discord.Member):
    response = await commands.search_helper(user.id)
    await interaction.response.send_message(response, ephemeral=False)

