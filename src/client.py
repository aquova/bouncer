import discord
from discord import app_commands as ac
from discord.ext import commands

import db
from singletons import singletons
import logs
from logtypes import LogTypes
from report import ReportModal
import reply
from say import SayModal
from visualize import post_plots
from utils import interaction_response_helper


HELP_MESSAGE = (
    "# Bouncer Slash Command Reference\n"
    "`/help` - Print this message\n"
    "## Logging\n"
    "`/log` - Log a user infraction\n"
    "`/note` - Add a user note\n"
    "`/scam` - Log a scam\n"
    "`/search` - Search for a user's logs\n"
    "`/edit` - Edit an incorrect log\n"
    "`/remove` - Remove a log\n"
    "`/alt` - Link two accounts together as alts\n"
    "## Messaging Users\n"
    "`/dm` - Send a DM to a user\n"
    "`/reply` - Reply to the owner of a DM thread\n"
    "`/preview` - Preview DM message sent to a user\n"
    "`/open` - Get a user's DM thread\n"
    "`/id` - Fetch the ID of a user in a DM thread\n"
    "`/waiting` - List users who are waiting for a reply\n"
    "`/clear` - Clear list of users waiting for reply\n"
    "## Misc.\n"
    "`/graph` - Post graphs of moderator activity\n"
    "`/say` - Post a message as the bot\n"
    "`/unmute` - Remove a user's timeout\n"
    "`/block` - Change if a user can DM the bot\n"
    "`/watch` - Change if a user is on the watchlist\n"
    "`/watchlist` - Print out the watchlist\n"
)

class DiscordClient(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        # The command prefix is never used, but we have to have something
        super().__init__(command_prefix="$", intents=intents)
        db.initialize()

    async def set_channels(self):
        await singletons.set_channels(self)

    async def sync_guild(self, guild: discord.Guild):
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

client = DiscordClient()

### Slash Commands
@client.tree.command(name="alt", description="Notes a user as an alt for another")
@ac.describe(a="Account A", b="Account B")
async def alt_slash(interaction: discord.Interaction, a: discord.User, b: discord.User):
    db.add_alt(a.id, b.id)
    await interaction_response_helper(interaction, f"`{str(a)}` has now been identified as an alt of `{str(b)}` (and vice versa)")

@client.tree.command(name="block", description="Change if user can DM us")
@ac.describe(user="User", block="Block?")
async def block_slash(interaction: discord.Interaction, user: discord.User, block: bool):
    response = singletons.blocks.handle_block(user, block)
    await interaction_response_helper(interaction, response)

@client.tree.command(name="clear", description="Clear list of users waiting for reply")
async def clear_slash(interaction: discord.Interaction):
    singletons.am.clear_entries()
    await interaction_response_helper(interaction, "Cleared waiting messages!")

@client.tree.command(name="dm", description="Send a DM to a user")
@ac.describe(user="User", message="Message")
async def dm_slash(interaction: discord.Interaction, user: discord.User, message: str):
    if interaction.channel_id is None: # Only for the linter's sake
        return
    await interaction.response.defer()
    response = await reply.dm(interaction.client, user, message, interaction.channel_id)
    await interaction_response_helper(interaction, response)

@client.tree.command(name="dm-popup", description="Send a DM to a user, with a popup")
async def popup_slash(interaction: discord.Interaction, user: discord.User):
    await interaction.response.send_modal(reply.DmModal(user))

@client.tree.command(name="edit", description="Edit an incorrect log")
@ac.describe(user="User", message="New log entry", index="Log index to edit")
async def edit_slash(interaction: discord.Interaction, user: discord.User, message: str, index: int):
    response = logs.edit_log(user, index, message, interaction.user)
    await interaction_response_helper(interaction, response)

@client.tree.command(name="graph", description="Post graphs of moderator activity")
async def graph_slash(interaction: discord.Interaction):
    await post_plots(interaction.response)

@client.tree.command(name="help", description="Post the help message")
async def help_slash(interaction: discord.Interaction):
    await interaction.response.send_message(HELP_MESSAGE)

@client.tree.command(name="id", description="Fetch the user ID of this DM thread")
async def id_slash(interaction: discord.Interaction):
    if interaction.channel_id is None: # Only for linter's sake
        return
    response = reply.get_id(interaction.client, interaction.channel_id)
    await interaction_response_helper(interaction, response)

# Note and Scam have their own separate commands:
# - Scam is meant to be a shortcut with fewer fields
# - Notes don't send DMs to their targets, so keep it separate in case of misclicks
@client.tree.command(name="log", description="Log a user infraction")
@ac.describe(user="User", reason="Reason for log", log_type="Type of log")
@ac.choices(log_type=[
    ac.Choice(name="Ban", value=LogTypes.BAN),
    ac.Choice(name="Warn", value=LogTypes.WARN),
    ac.Choice(name="Kick", value=LogTypes.KICK),
    ac.Choice(name="Unban", value=LogTypes.UNBAN),
])
async def log_slash(interaction: discord.Interaction, user: discord.User, reason: str, log_type: LogTypes):
    if interaction.channel_id is None:
        return
    # Logging is a fairly intensive task, with potentially several items that requires us to wait on Discord
    # To that end, defer the response, so that it doesn't take too long and indicate to the user it failed
    await interaction.response.defer()
    response = await logs.log_user(interaction.client, user, reason, log_type, interaction.user, interaction.channel_id)
    await interaction_response_helper(interaction, response)

@client.tree.command(name="note", description="Add a user note")
@ac.describe(user="User", note="Note to add")
async def note_slash(interaction: discord.Interaction, user: discord.User, note: str):
    if interaction.channel_id is None:
        return
    await interaction.response.defer()
    response = await logs.log_user(interaction.client, user, note, LogTypes.NOTE, interaction.user, interaction.channel_id)
    await interaction_response_helper(interaction, response)

@client.tree.command(name="open", description="Get user's reply thread")
@ac.describe(user="User")
async def open_slash(interaction: discord.Interaction, user: discord.User):
    response = await reply.show_reply_thread(user)
    await interaction_response_helper(interaction, response)

@client.tree.command(name="preview", description="Prints out a DM message as the user will receive it")
@ac.describe(reason="Reason for logging", log_type="Log type")
async def preview_slash(interaction: discord.Interaction, reason: str, log_type: LogTypes):
    response = logs.preview(reason, log_type)
    await interaction_response_helper(interaction, response)

@client.tree.command(name="remove", description="Remove a log")
@ac.describe(user="User", index="Log index to remove")
async def remove_slash(interaction: discord.Interaction, user: discord.User, index: int):
    response = await logs.remove_error(user, index)
    await interaction_response_helper(interaction, response)

@client.tree.command(name="reply", description="Reply to a user from within their thread")
@ac.describe(message="Message")
async def reply_slash(interaction: discord.Interaction, message: str):
    if interaction.channel_id is None: # Only for the linter's sake
        return
    response = await reply.reply(interaction.client, message, interaction.channel_id)
    await interaction_response_helper(interaction, response)

@client.tree.command(name="say", description="Say a message as the bot")
@ac.describe(channel="Channel to post in")
async def say_slash(interaction: discord.Interaction, channel: discord.TextChannel | discord.Thread):
    await interaction.response.send_modal(SayModal(channel))

@client.tree.command(name="scam", description="Log a scam")
@ac.describe(user="User")
async def scam_slash(interaction: discord.Interaction, user: discord.User):
    if interaction.channel_id is None:
        return
    await interaction.response.defer()
    response = await logs.log_user(interaction.client, user, "", LogTypes.SCAM, interaction.user, interaction.channel_id)
    await interaction_response_helper(interaction, response)

@client.tree.command(name="search", description="Search for a user's logs")
@ac.describe(user="User")
async def search_slash(interaction: discord.Interaction, user: discord.User):
    response = logs.search_logs(user)
    await interaction_response_helper(interaction, response)

@client.tree.command(name="unmute", description="Remove a user's timeout")
@ac.describe(user="User")
async def unmute_slash(interaction: discord.Interaction, user: discord.Member):
    response = await singletons.spammers.unmute(user)
    await interaction_response_helper(interaction, response)

@client.tree.command(name="waiting", description="List users who are waiting for a reply")
async def waiting_slash(interaction: discord.Interaction):
    response = singletons.am.list_waiting()
    await interaction_response_helper(interaction, response)

@client.tree.command(name="watch", description="Edit the watchlist")
@ac.describe(user="User", watch="Watch?")
async def watch_slash(interaction: discord.Interaction, user: discord.User, watch: bool):
    response = singletons.watch.handle_watch(user, watch)
    await interaction_response_helper(interaction, response)

@client.tree.command(name="watchlist", description="Print out the watchlist")
async def watchlist_slash(interaction: discord.Interaction):
    response = singletons.watch.get_watchlist()
    await interaction_response_helper(interaction, response)

### Context commands ###
@client.tree.context_menu(name="Report")
async def report_context(interaction: discord.Interaction, message: discord.Message):
    await interaction.response.send_modal(ReportModal(message=message))

@client.tree.context_menu(name="Report Message")
async def report_message_context(interaction: discord.Interaction, _: discord.Member):
    await interaction.response.send_message("If you want to report someone, you need to select the message, not the user.", ephemeral=True)
