import discord

from client import client
import commands
from logtypes import LogTypes
from report import ReportModal
from visualize import post_plots

### Slash Commands
@client.tree.command(name="ban", description="Log a user ban")
@discord.app_commands.describe(user="User", reason="Reason for banning")
async def ban_slash(interaction: discord.Interaction, user: discord.Member, reason: str):
    response = await commands.log_user(user, reason, LogTypes.BAN, interaction.user)
    await interaction.response.send_message(response)

@client.tree.command(name="block", description="Change if user can DM us")
@discord.app_commands.describe(user="User", block="Block?")
async def block_slash(interaction: discord.Interaction, user: discord.Member, block: bool):
    response = client.blocks.handle_block(user, block)
    await interaction.response.send_message(response)

@client.tree.command(name="graph", description="Post graphs of moderator activity")
async def graph_slash(interaction: discord.Interaction):
    await post_plots(interaction.response)

@client.tree.command(name="kick", description="Log a user kick")
@discord.app_commands.describe(user="User", reason="Reason for kicking")
async def kick_slash(interaction: discord.Interaction, user: discord.Member, reason: str):
    response = await commands.log_user(user, reason, LogTypes.KICK, interaction.user)
    await interaction.response.send_message(response)

@client.tree.command(name="note", description="Add a user note")
@discord.app_commands.describe(user="User", note="Note to add")
async def note_slash(interaction: discord.Interaction, user: discord.Member, note: str):
    response = await commands.log_user(user, note, LogTypes.NOTE, interaction.user)
    await interaction.response.send_message(response)

@client.tree.command(name="scam", description="Log a scam")
@discord.app_commands.describe(user="User")
async def scam_slash(interaction: discord.Interaction, user: discord.Member):
    response = await commands.log_user(user, "", LogTypes.SCAM, interaction.user)
    await interaction.response.send_message(response)

@client.tree.command(name="search", description="Search for a user's logs")
@discord.app_commands.describe(user="User")
async def search_slash(interaction: discord.Interaction, user: discord.Member):
    response = commands.search_logs(user)
    await interaction.response.send_message(response)

@client.tree.command(name="unban", description="Log a user unbanning")
@discord.app_commands.describe(user="User", reason="Reason for unbanning")
async def unban_slash(interaction: discord.Interaction, user: discord.Member, reason: str):
    response = await commands.log_user(user, reason, LogTypes.UNBAN, interaction.user)
    await interaction.response.send_message(response)

@client.tree.command(name="warn", description="Log a user warn")
@discord.app_commands.describe(user="User", reason="Reason for warning")
async def warn_slash(interaction: discord.Interaction, user: discord.Member, reason: str):
    response = await commands.log_user(user, reason, LogTypes.WARN, interaction.user)
    await interaction.response.send_message(response)

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
