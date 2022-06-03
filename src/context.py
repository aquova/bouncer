import discord
from client import client

@client.tree.context_menu(name="Test")
async def test(interaction: discord.Interaction, message: discord.Message):
    await interaction.response.send_message("Look, it worked", ephemeral=False)

