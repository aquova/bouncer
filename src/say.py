import discord

from utils import CHAR_LIMIT

class SayModal(discord.ui.Modal):
    def __init__(self, channel: discord.TextChannel | discord.Thread):
        super().__init__(title="Say a message as the bot")
        self.channel = channel
        self.content = discord.ui.TextInput(
            label="Bot message",
            style=discord.TextStyle.long,
            max_length=CHAR_LIMIT,
            required=True,
        )
        self.add_item(self.content)

    async def on_submit(self, interaction: discord.Interaction):
        await self.channel.send(self.content.value)
        await interaction.response.send_message("Message sent!")
