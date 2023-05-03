import discord
from client import client
from config import MAILBOX
from commonbot.utils import combine_message, send_message

class ReportModal(discord.ui.Modal):
    def __init__(self, *, message: discord.Message):
        super().__init__(title="Report a message")

        self.message: discord.Message = message
        self.comments_input: discord.ui.TextInput = discord.ui.TextInput(
            label="Comments",
            placeholder="(Optional) Additional comments or context",
            style=discord.TextStyle.long,
            required=False,
            max_length=250
        )
        self.add_item(self.comments_input)

    async def on_submit(self, interaction: discord.Interaction):
        embed: discord.Embed = discord.Embed(
            title=f"\N{BALLOT BOX WITH BALLOT} Report from #{self.message.channel.name}",
            colour=discord.Colour.gold(),
            url=self.message.jump_url)

        message_str: str = combine_message(self.message)
        comments_str: str = self.comments_input.value

        len_max: int = 1000
        [
            embed.add_field(
                name=field[0],
                value=field[1] if len(field[1]) < len_max else f"{field[1][:len_max-1]}…",
                inline=field[2])
            for field in [
                ("Suspect", self.message.author.mention, True),
                ("Reported by", interaction.user.mention, True),
                (f"Sent <t:{int(self.message.created_at.timestamp())}:R>:", message_str, False),
                ("Comments:", comments_str, False)
            ] if field[1]
        ]

        log_chan = interaction.guild.get_channel(MAILBOX)
        await log_chan.send(embed=embed)
        await interaction.response.send_message(
            content="Your report has been forwarded to the server staff. Thanks!",
            ephemeral=True)


@client.tree.context_menu(name="Report")
async def report_context(interaction: discord.Interaction, message: discord.Message):
    await interaction.response.send_modal(ReportModal(message=message))
