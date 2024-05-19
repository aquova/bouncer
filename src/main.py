# Bouncer
# https://github.com/aquova/bouncer
# 2018-2024

from datetime import datetime, timezone

import discord
import humanize

import config
from client import client
from forwarder import message_forwarder
import utils

"""
Delete message

A helper function that deletes and logs the given message
"""
async def delete_message_helper(message: discord.Message):
    timedelta = datetime.now(timezone.utc) - message.created_at
    mes = f":no_mobile_phones: **{str(message.author)}** deleted " \
          f"in <#{message.channel.id}>: `{message.content}` \n" \
          f":timer: This message was visible for {humanize.precisedelta(timedelta)}."
    # Adds URLs for any attachments that were included in deleted message
    # These will likely become invalid, but it's nice to note them anyway
    if message.attachments:
        for item in message.attachments:
            mes += '\n' + item.url

    client.syslog.add_log(mes)

"""
Should Log

Whether the bot should log this event in config.SYS_LOG
"""
def should_log(server: discord.Guild) -> bool:
    if not server:
        return False
    return server.id == config.HOME_SERVER

"""
On Ready

Occurs when Discord bot is first brought online
"""
@client.event
async def on_ready():
    print('Logged in as')
    if client.user:
        print(client.user.name)
        print(client.user.id)

    # Set Bouncer's activity status
    activity_object = discord.Activity(name="for your reports!", type=discord.ActivityType.watching)
    await client.change_presence(activity=activity_object)

    await client.set_channels()

"""
On Guild Available

Runs when a guild (server) becomes available to the bot
"""
@client.event
async def on_guild_available(guild: discord.Guild):
    await client.sync_guild(guild)

"""
On Thread Create

Occurs when a new thread is created in the server
"""
@client.event
async def on_thread_create(thread: discord.Thread):
    await thread.join()
    await thread.edit(auto_archive_duration=10080) # Set all new threads to maximum timeout

"""
On Member Update

Occurs when a user updates an attribute (nickname, roles, timeout)
"""
@client.event
async def on_member_update(before: discord.Member, after: discord.Member):
    if not should_log(before.guild):
        return

    # If nickname has changed
    if before.nick != after.nick:
        # If they don't have an ending nickname, they reset to their actual username
        if not after.nick:
            mes = f"**:spy: {str(after)}** has reset their username"
        else:
            mes = f"**:spy: {str(after)}** is now known as `{after.nick}`"
        client.syslog.add_log(mes)
    # If role quantity has changed
    elif before.roles != after.roles:
        # Determine role difference, post about it
        removed = [r.name for r in before.roles if r not in after.roles]
        added = [r.name for r in after.roles if r not in before.roles]
        mes = ""
        if removed:
            removed_str = ', '.join(removed)
            mes += f":no_entry_sign: **{str(after)}** had the role(s) `{removed_str}` removed.\n"

        if added:
            added_str = ', '.join(added)
            mes += f":new: **{str(after)}** had the role(s) `{added_str}` added."

        if mes != "":
            client.syslog.add_log(mes)
    # If they were timed out
    # Note, this won't trip when the timeout wears off, due to a Discord limitation
    if before.timed_out_until != after.timed_out_until:
        if after.timed_out_until:
            timedelta = after.timed_out_until - datetime.now(timezone.utc)
            timeout_str = humanize.precisedelta(timedelta, minimum_unit="seconds", format="%d")
            mes = f":zipper_mouth: {str(after)} has been timed out for {timeout_str}."
            client.syslog.add_log(mes)
        else:
            client.syslog.add_log(f":grin: {str(after)} is no longer timed out.")

"""
On Member Ban

Occurs when a user is banned
"""
@client.event
async def on_member_ban(server: discord.Guild, member: discord.Member):
    if not should_log(server):
        return

    # We can remove banned user from our answering machine and watch list (if they exist)
    client.am.remove_entry(member.id)
    client.watch.remove_user(member.id)

    mes = f":newspaper2: **{str(member)} ({member.id})** has been banned."
    client.syslog.add_log(mes)

"""
On Member Remove

Occurs when a user leaves the server
"""
@client.event
async def on_member_remove(member: discord.Member):
    if not should_log(member.guild):
        return

    # We can remove left users from our answering machine
    client.am.remove_entry(member.id)

    if client.watch.should_note(member.id):
        await utils.send_message(f"{str(member)} has left the server.", client.watchlist)

    mes = f":wave: **{str(member)} ({member.id})** has left"
    client.syslog.add_log(mes)

"""
On Message Delete

Occurs when a user's message is deleted
"""
@client.event
async def on_message_delete(message: discord.Message):
    if message.guild and not should_log(message.guild) or message.author.bot:
        return

    await delete_message_helper(message)

"""
On Bulk Message Delete

Occurs when a user's messages are bulk deleted, such as ban or kick
"""
@client.event
async def on_bulk_message_delete(messages: list[discord.Message]):
    if messages[0].guild and not should_log(messages[0].guild) or messages[0].author.bot:
        return

    for message in messages:
        await delete_message_helper(message)

"""
On Message Edit

Occurs when a user edits a message
"""
@client.event
async def on_message_edit(before: discord.Message, after: discord.Message):
    if before.guild and not should_log(before.guild) or before.author.bot:
        return

    # Prevent embedding of content from triggering the log
    if before.content == after.content:
        return

    # Forward an edit to a DM
    if isinstance(after.channel, discord.channel.DMChannel):
        await message_forwarder.on_dm(after, True)
        return

    try:
        mes = f":pencil: **{str(before.author)}** modified in <#{before.channel.id}>: `{before.content}` to `{after.content}`"
        client.syslog.add_log(mes)

        # If user is on watchlist, then post it there as well
        watching = client.watch.should_note(after.author.id)
        if watching:
            await utils.send_message(mes, client.watchlist)

    except discord.errors.HTTPException as err:
        print(f"Unknown error with editing message. This message was unable to post for this reason: {err}\n")

"""
On Member Join

Occurs when a user joins the server
"""
@client.event
async def on_member_join(member: discord.Member):
    if not should_log(member.guild):
        return

    if client.watch.should_note(member.id):
        await utils.send_message(f"{str(member)} has joined the server.", client.watchlist)

    mes = f":confetti_ball: **{str(member)} ({member.id})** has joined"
    client.syslog.add_log(mes)

"""
On Voice State Update

Occurs when a user joins/leaves an audio channel
"""
@client.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    if not should_log(member.guild) or member.bot:
        return

    if not after.channel:
        mes = f":mute: **{str(member)}** has left voice channel {before.channel.name}"
        client.syslog.add_log(mes)
    elif not before.channel:
        mes = f":loud_sound: **{str(member)}** has joined voice channel {after.channel.name}"
        client.syslog.add_log(mes)

"""
On Reaction Remove

Occurs when a user removes a reaction from a message
"""
@client.event
async def on_reaction_remove(reaction: discord.Reaction, user: discord.Member):
    if user.bot:
        return

    emoji_name = reaction.emoji if isinstance(reaction.emoji, str) else reaction.emoji.name
    client.syslog.add_log(f":face_in_clouds: {str(user)} ({user.id}) removed the `{emoji_name}` emoji")

"""
On Message

Occurs when a user posts a message
More or less the main function
"""
@client.event
async def on_message(message: discord.Message):
    # Bouncer should not react to its own messages
    if message.author.id == client.user.id:
        return

    # If bouncer detects a private DM sent to it, forward it to staff
    if isinstance(message.channel, discord.channel.DMChannel):
        await message_forwarder.on_dm(message)
        return

    (spammed, spam_message) = await client.spammers.check_spammer(message)
    if spammed:
        await client.spam.send(spam_message)
        return

    # Check if user is on watchlist, and should be tracked
    watching = client.watch.should_note(message.author.id)
    if watching:
        content = utils.combine_message(message)
        mes = f"<@{str(message.author.id)}> said in <#{message.channel.id}>: {content}"
        await utils.send_message(mes, client.watchlist)

    # If a user pings bouncer, log into mod channel
    if client.user in message.mentions:
        embed: discord.Embed = discord.Embed(
            title=f"\N{DIGIT ONE}\u20E3 Pinged by {message.author.global_name or message.author}",
            description=f"{message.content if len(message.content) <= 99 else message.content[:99] + '…'}",
            colour=discord.Colour.blue(),
            url=message.jump_url)
        await client.mailbox.send(embed=embed)

client.run(config.DISCORD_KEY)
