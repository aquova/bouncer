from datetime import datetime
from typing import cast

import discord

from client import client
from commonbot.utils import combine_message
from forwarder import message_forwarder

class ReportResolveButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Resolve",
            style=discord.ButtonStyle.success
        )

    async def callback(self, interaction: discord.Interaction):
        if not interaction.message:
            return
        embed: discord.Embed = interaction.message.embeds[0]
        embed.colour = discord.Colour.dark_green()
        if embed.title is not None:
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
    def __init__(self, *, reported_user: discord.User | discord.Member, thread_url: str | None = None):
        super().__init__(
            label="Thread",
            style=discord.ButtonStyle.link if thread_url else discord.ButtonStyle.secondary,
            emoji=None if thread_url else "\N{LEFT-POINTING MAGNIFYING GLASS}",
            url=thread_url
        )
        self.reported_user: discord.User | discord.Member = reported_user

    async def callback(self, interaction: discord.Interaction):
        if self.url is None:
            thread: discord.Thread = await message_forwarder.get_or_create_user_reply_thread(
                user=self.reported_user
            )

            view: discord.ui.View = self.view
            view.remove_item(self)
            view.add_item(ReportThreadButton(
                reported_user=self.reported_user,
                thread_url=thread.jump_url if thread else None)
            )
            if interaction.message is not None:
                await interaction.message.edit(view=view)
            await interaction.response.defer()


class ReportMailboxView(discord.ui.View):
    def __init__(self, *, reported_user: discord.User | discord.Member):
        super().__init__(timeout=0)

        thread_id: int | None = message_forwarder.get_reply_thread_id_for_user(user=reported_user)
        thread: discord.Thread | None = cast(discord.Thread, client.get_channel(thread_id)) if thread_id else None
        self.thread_button = ReportThreadButton(
            reported_user=reported_user,
            thread_url=thread.jump_url if thread else None)
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

        reported_user: discord.User | discord.Member = self.message.author
        message_str: str = combine_message(self.message)
        comments_str: str = self.comments_input.value

        len_max: int = 1000
        [
            embed.add_field(
                name=field[0],
                value=field[1] if len(field[1]) < len_max else f"{field[1][:len_max-1]}…",
                inline=field[2])
            for field in [
                ("Suspect", reported_user.mention, True),
                ("Reported by", interaction.user.mention, True),
                (f"Sent <t:{int(self.message.created_at.timestamp())}:R>:", message_str, False),
                ("Comments:", comments_str, False)
            ] if field[1]
        ]

        await client.mailbox.send(embed=embed, view=ReportMailboxView(reported_user=reported_user))
        await interaction.response.send_message(
            content="Your report has been forwarded to the server staff. Thanks!",
            ephemeral=True)

