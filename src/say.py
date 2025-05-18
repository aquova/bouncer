import discord
from typing import override

from utils import CHAR_LIMIT

class SayModal(discord.ui.Modal):
    def __init__(self, channel: discord.TextChannel | discord.Thread):
        super().__init__(title="Say a message as the bot")
        self.channel: discord.TextChannel | discord.Thread = channel
        self.content: discord.ui.TextInput[discord.ui.View] = discord.ui.TextInput(
            label="Bot message",
            style=discord.TextStyle.long,
            max_length=CHAR_LIMIT,
            required=True,
        )
        self.add_item(self.content)

    @override
    async def on_submit(self, interaction: discord.Interaction):
        await self.channel.send(self.content.value)
        await interaction.response.send_message("Message sent!")
