from datetime import datetime

import discord

from client import client
from config import MAILBOX
from commonbot.utils import combine_message
from forwarder import message_forwarder

class ReportResolveButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Resolve",
            style=discord.ButtonStyle.success
        )

    async def callback(self, interaction: discord.Interaction):
        embed: discord.Embed = interaction.message.embeds[0]
        embed.colour = discord.Colour.dark_green()
        embed.title = f"\N{WHITE HEAVY CHECK MARK}{embed.title[1:]}"
        embed.add_field(
            name=f"Resolved <t:{int(datetime.now().timestamp())}:R> by",
            value=interaction.user.mention,
            inline=False
        )

        view: discord.ui.View = self.view
        view.remove_item(self)
        await interaction.message.edit(embed=embed, view=view)

        await interaction.response.defer()


class ReportThreadButton(discord.ui.Button):
    def __init__(self, *, thread_url: str = None, reported_user: discord.User = None):
        super().__init__(
            label="Thread",
            style=discord.ButtonStyle.link if thread_url else discord.ButtonStyle.secondary,
            emoji=None if thread_url else "\N{LEFT-POINTING MAGNIFYING GLASS}",
            url=thread_url
        )
        self.reported_user: discord.User = reported_user

    async def callback(self, interaction: discord.Interaction):
        if self.url is None:
            log_chan = interaction.guild.get_channel(MAILBOX)
            thread: discord.Thread = await message_forwarder.get_or_create_user_reply_thread(
                user=self.reported_user,
                parent_channel=log_chan
            )

            view: discord.ui.View = self.view
            view.remove_item(self)
            view.add_item(ReportThreadButton(thread_url=thread.jump_url))
            await interaction.message.edit(view=view)

            await interaction.response.defer()


class ReportMailboxView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=0)

        self.thread_button = ReportThreadButton()
        self.add_item(ReportResolveButton())
        self.add_item(self.thread_button)


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
        await log_chan.send(embed=embed, view=ReportMailboxView())
        await interaction.response.send_message(
            content="Your report has been forwarded to the server staff. Thanks!",
            ephemeral=True)


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
