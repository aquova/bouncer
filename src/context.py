import discord

from client import client
from report import ReportModal
from visualize import post_plots

### Slash Commands
@client.tree.command(name="block", description="Change if user can DM us")
@discord.app_commands.describe(user="User", block="Block?")
async def block_slash(interaction: discord.Interaction, user: discord.Member, block: bool):
    response = client.blocks.handle_block(user, block)
    await interaction.response.send_message(response)

@client.tree.command(name="graph", description="Post graphs of moderator activity")
async def graph_slash(interaction: discord.Interaction):
    await post_plots(interaction.response)

@client.tree.command(name="watch", description="Edit the watchlist")
@discord.app_commands.describe(user="User", watch="Watch?")
async def watch_slash(interaction: discord.Interaction, user: discord.Member, watch: bool):
    response = client.watch.handle_watch(user, watch)
    await interaction.response.send_message(response)

@client.tree.command(name="watchlist", description="Print out the watchlist")
async def watchlist_slash(interaction: discord.Interaction):
    response = client.watch.get_watchlist()
    await interaction.response.send_message(response)

### Context commands ###
@client.tree.context_menu(name="Report")
async def report_context(interaction: discord.Interaction, message: discord.Message):
    await interaction.response.send_modal(ReportModal(message=message))

@client.tree.context_menu(name="Report Message")
async def report_message_context(interaction: discord.Interaction, _: discord.Member):
    await interaction.response.send_message("If you want to report someone, you need to select the message, not the user.", ephemeral=True)
