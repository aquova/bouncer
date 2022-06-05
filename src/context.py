import discord
from client import client
import commands

@client.tree.context_menu(name="Search")
@discord.app_commands.default_permissions() # Only allow admins to use this command
async def search_context(interaction: discord.Interaction, user: discord.Member):
    response = await commands.search_helper(user.id)
    await interaction.response.send_message(response, ephemeral=True)

