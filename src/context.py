import discord

from client import client
import commands
from config import ADMIN_CATEGORIES
from logtypes import LogTypes
from report import ReportModal
from visualize import post_plots
from utils import CHAR_LIMIT, split_message

# Interaction wrapper that prevents users from leaking info
async def interaction_response_helper(interaction: discord.Interaction, response: str):
    if interaction.channel.category.id in ADMIN_CATEGORIES:
        if len(response) > CHAR_LIMIT:
            messages = split_message(response)
            await interaction.response.send_message(messages[0])
            followup = interaction.followup
            for m in messages[1:]:
                await followup.send(m)
        else:
            await interaction.response.send_message(response)
    else:
        await interaction.response.send_message("Don't leak info!", ephemeral=True)

### Slash Commands
@client.tree.command(name="block", description="Change if user can DM us")
@discord.app_commands.describe(user="User", block="Block?")
async def block_slash(interaction: discord.Interaction, user: discord.User, block: bool):
    response = client.blocks.handle_block(user, block)
    await interaction_response_helper(interaction, response)

@client.tree.command(name="clear", description="Clear list of users waiting for reply")
async def clear_slash(interaction: discord.Interaction):
    client.am.clear_entries()
    await interaction_response_helper(interaction, "Cleared waiting messages!")

@client.tree.command(name="dm", description="Send a DM to a user")
@discord.app_commands.describe(user="User", message="Message")
async def dm_slash(interaction: discord.Interaction, user: discord.User, message: str):
    if interaction.channel_id is None: # Only for the linter's sake
        return
    response = await commands.dm(user, message, interaction.channel_id)
    await interaction_response_helper(interaction, response)

@client.tree.command(name="edit", description="Edit an incorrect log")
@discord.app_commands.describe(user="User", message="New log entry", index="Log index to edit")
async def edit_slash(interaction: discord.Interaction, user: discord.User, message: str, index: int):
    response = commands.edit_log(user, index, message, interaction.user)
    await interaction_response_helper(interaction, response)

@client.tree.command(name="graph", description="Post graphs of moderator activity")
async def graph_slash(interaction: discord.Interaction):
    await post_plots(interaction.response)

# Note and Scam have their own separate commands:
# - Scam is meant to be a shortcut with fewer fields
# - Notes don't send DMs to their targets, so keep it separate in case of misclicks
@client.tree.command(name="log", description="Log a user infraction")
@discord.app_commands.describe(user="User", reason="Reason for log", log_type="Type of log")
@discord.app_commands.choices(log_type=[
    discord.app_commands.Choice(name="Ban", value=LogTypes.BAN),
    discord.app_commands.Choice(name="Warn", value=LogTypes.WARN),
    discord.app_commands.Choice(name="Kick", value=LogTypes.KICK),
    discord.app_commands.Choice(name="Unban", value=LogTypes.UNBAN),
])
async def log_slash(interaction: discord.Interaction, user: discord.User, reason: str, log_type: LogTypes):
    if interaction.channel_id is None:
        return
    response = await commands.log_user(user, reason, log_type, interaction.user, interaction.channel_id)
    await interaction_response_helper(interaction, response)

@client.tree.command(name="note", description="Add a user note")
@discord.app_commands.describe(user="User", note="Note to add")
async def note_slash(interaction: discord.Interaction, user: discord.User, note: str):
    if interaction.channel_id is None:
        return
    response = await commands.log_user(user, note, LogTypes.NOTE, interaction.user, interaction.channel_id)
    await interaction_response_helper(interaction, response)

@client.tree.command(name="open", description="Get user's reply thread")
@discord.app_commands.describe(user="User")
async def open_slash(interaction: discord.Interaction, user: discord.User):
    response = await commands.show_reply_thread(user)
    await interaction_response_helper(interaction, response)

@client.tree.command(name="preview", description="Prints out a DM message as the user will receive it")
@discord.app_commands.describe(reason="Reason for logging", log_type="Log type")
async def preview_slash(interaction: discord.Interaction, reason: str, log_type: LogTypes):
    response = commands.preview(reason, log_type)
    await interaction_response_helper(interaction, response)

@client.tree.command(name="remove", description="Remove a log")
@discord.app_commands.describe(user="User", index="Log index to remove")
async def remove_slash(interaction: discord.Interaction, user: discord.User, index: int):
    response = await commands.remove_error(user, index)
    await interaction_response_helper(interaction, response)

@client.tree.command(name="reply", description="Reply to a user from within their thread")
@discord.app_commands.describe(message="Message")
async def reply_slash(interaction: discord.Interaction, message: str):
    if interaction.channel_id is None: # Only for the linter's sake
        return
    response = await commands.reply(message, interaction.channel_id)
    await interaction_response_helper(interaction, response)

@client.tree.command(name="say", description="Say a message as the bot")
@discord.app_commands.describe(message="Message to say", channel="Channel to post in")
async def say_slash(interaction: discord.Interaction, message: str, channel: discord.TextChannel | discord.Thread):
    await channel.send(message)
    await interaction_response_helper(interaction, "Message sent!")

@client.tree.command(name="scam", description="Log a scam")
@discord.app_commands.describe(user="User")
async def scam_slash(interaction: discord.Interaction, user: discord.User):
    if interaction.channel_id is None:
        return
    response = await commands.log_user(user, "", LogTypes.SCAM, interaction.user, interaction.channel_id)
    await interaction_response_helper(interaction, response)

@client.tree.command(name="search", description="Search for a user's logs")
@discord.app_commands.describe(user="User")
async def search_slash(interaction: discord.Interaction, user: discord.User):
    response = commands.search_logs(user)
    await interaction_response_helper(interaction, response)

@client.tree.command(name="unmute", description="Remove a user's timeout")
@discord.app_commands.describe(user="User")
async def unmute_slash(interaction: discord.Interaction, user: discord.Member):
    response = await client.spammers.unmute(user)
    await interaction_response_helper(interaction, response)

@client.tree.command(name="waiting", description="List users who are waiting for a reply")
async def waiting_slash(interaction: discord.Interaction):
    response = client.am.list_waiting()
    await interaction_response_helper(interaction, response)

@client.tree.command(name="watch", description="Edit the watchlist")
@discord.app_commands.describe(user="User", watch="Watch?")
async def watch_slash(interaction: discord.Interaction, user: discord.Member, watch: bool):
    response = client.watch.handle_watch(user, watch)
    await interaction_response_helper(interaction, response)

@client.tree.command(name="watchlist", description="Print out the watchlist")
async def watchlist_slash(interaction: discord.Interaction):
    response = client.watch.get_watchlist()
    await interaction_response_helper(interaction, response)

### Context commands ###
@client.tree.context_menu(name="Report")
async def report_context(interaction: discord.Interaction, message: discord.Message):
    await interaction.response.send_modal(ReportModal(message=message))

@client.tree.context_menu(name="Report Message")
async def report_message_context(interaction: discord.Interaction, _: discord.Member):
    await interaction.response.send_message("If you want to report someone, you need to select the message, not the user.", ephemeral=True)
