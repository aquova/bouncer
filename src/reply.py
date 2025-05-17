import discord
from typing import override

from client import client
from config import SERVER_NAME
from forwarder import message_forwarder
from utils import CHAR_LIMIT, interaction_response_helper

class DmModal(discord.ui.Modal):
    def __init__(self, user: discord.User):
        super().__init__(title="DM a user")
        self.user: discord.User = user
        self.content = discord.ui.TextInput(
            label="DM Message",
            style=discord.TextStyle.long,
            max_length=CHAR_LIMIT,
            required=True,
        )
        self.add_item(self.content)

    @override
    async def on_submit(self, interaction: discord.Interaction):
        if interaction.channel_id is None: # Only for the linter's sake
            return
        response = await dm(self.user, self.content.value, interaction.channel_id)
        await interaction_response_helper(interaction, response)

"""
Show reply thread

Sends the the reply thread for a user so it's easy for staff to find
"""
async def show_reply_thread(user: discord.User) -> str:
    # Show reply thread if it exists
    reply_thread_id = message_forwarder.get_reply_thread_id_for_user(user)
    if reply_thread_id is None:
        return f"User <@{user.id}> does not have a reply thread."
    return f"Reply thread for <@{user.id}>: <#{reply_thread_id}>."

"""
Get user ID

Get's the user ID associated with the channel ID of the current DM thread
"""
def get_id(channel_id: int) -> str:
    user = _get_user_for_reply(channel_id)
    if user is None:
        return "I can't get this user's ID. Are we in a DM thread?"
    return str(user.id)

"""
DM

Sends a private message to the specified user
"""
async def dm(user: discord.User | discord.Member, message: str, channel_id: int) -> str:
    try:
        await user.send(f"A message from the {SERVER_NAME} staff: {message}")
        client.am.remove_entry(user.id)

        # Add context in the user's reply thread
        await add_context_to_reply_thread(channel_id, user, f"Message sent to `{str(user)}`", message)
        return f"Message sent to `{str(user)}`: {message}"
    except discord.errors.HTTPException as err:
        if err.code == 50007:
            return "Cannot send messages to this user. It is likely they have DM closed or I am blocked."
        else:
            return f"ERROR: While attempting to DM, there was an unexpected error: {err}"

"""
Reply

Sends a private message to the user whose DM thread this is
"""
async def reply(message: str, channel_id: int) -> str:
    user = _get_user_for_reply(channel_id)
    if user is None:
        return "This command can only be sent inside a DM thread. Try again there, or use the `/dm` command."
    response = await dm(user, message, channel_id)
    return response

"""
_add_context_to_reply_thread

Adds information about a moderation action taken on a specific user to the user's reply thread.

If the moderation action already happened in the user's reply thread, no more context is needed, so this does nothing.

Otherwise, it posts a message in the reply thread with the details of the action and a link to the source message.
"""
async def add_context_to_reply_thread(channel_id: int, user: discord.User | discord.Member, context: str, message: str):
    reply_thread_id = message_forwarder.get_reply_thread_id_for_user(user)
    if channel_id == reply_thread_id:
        return # Already in reply thread, nothing to do

    reply_thread = await message_forwarder.get_or_create_user_reply_thread(user, content=message)

    await reply_thread.send(f"{context}: {message}")

"""
_get_user_for_reply

Gets the user to reply to for a reply command.

Based on the channel it was sent in, this figures out who to DM.
"""
def _get_user_for_reply(channel_id: int) -> discord.User | discord.Member | None:
    # If it's a reply thread, the user the reply thread is for, otherwise None
    thread_user = message_forwarder.get_userid_for_user_reply_thread(channel_id)

    if thread_user is not None:
        return client.get_user(thread_user)
    return None
