import discord

from client import client
from report import ReportModal
from visualize import post_plots

@client.tree.command(name="block", description="Change if user can DM us")
@discord.app_commands.describe(user="User", block="Block?")
async def block_slash(interaction: discord.Interaction, user: discord.Member, block: bool):
    response = client.blocks.handle_block(user, block)
    await interaction.response.send_message(response)

@client.tree.command(name="graph", description="Post graphs of moderator activity")
async def graph_slash(interaction: discord.Interaction):
    await post_plots(interaction.response)

@client.tree.context_menu(name="Report")
async def report_context(interaction: discord.Interaction, message: discord.Message):
    await interaction.response.send_modal(ReportModal(message=message))

@client.tree.context_menu(name="Report Message")
async def report_message_context(interaction: discord.Interaction, _: discord.Member):
    await interaction.response.send_message("If you want to report someone, you need to select the message, not the user.", ephemeral=True)
