# Bouncer
# Written by aquova, 2018-2021
# https://github.com/aquova/bouncer

import discord, traceback
import censor, commands, config, db, visualize
import commonbot.utils
from censor import check_censor
from config import LogTypes
from waiting import AnsweringMachineEntry
from watcher import Watcher

from commonbot.debug import Debug
from commonbot.timekeep import Timekeeper

intents = discord.Intents.default()
intents.members = True

# Initialize client and helper classes
client = discord.Client(intents=intents)
db.initialize()
dbg = Debug(config.OWNER, config.CMD_PREFIX, config.DEBUG_BOT)
tk = Timekeeper()
watch = Watcher()

FUNC_DICT = {
    "ban":         [commands.logUser,              LogTypes.BAN],
    "block":       [commands.blockUser,            True],
    "censor":      [censor.listCensor,             None],
    "clear":       [commands.am.clear_entries,     None],
    "edit":        [commands.removeError,          True],
    "graph":       [visualize.post_plots,          None],
    "help":        [commands.send_help_mes,        None],
    "kick":        [commands.logUser,              LogTypes.KICK],
    "note":        [commands.logUser,              LogTypes.NOTE],
    "preview":     [commands.preview,              None],
    "remove":      [commands.removeError,          False],
    "reply":       [commands.reply,                None],
    "search":      [commands.userSearch,           None],
    "unban":       [commands.logUser,              LogTypes.UNBAN],
    "unblock":     [commands.blockUser,            False],
    "uptime":      [tk.uptime,                     None],
    "waiting":     [commands.am.gen_waiting_list,  None],
    "warn":        [commands.logUser,              LogTypes.WARN],
    "watch":       [watch.watch_user,              None],
    "watchlist":   [watch.get_watchlist,           None],
    "unwatch":     [watch.unwatch_user,            None],
}

"""
Delete message

A helper function that deletes and logs the given message
"""
async def delete_message_helper(message):
    mes = f":no_mobile_phones: **{str(message.author)}** deleted in <#{message.channel.id}>: `{message.content}`"
    chan = client.get_channel(config.SYS_LOG)
    # Adds URLs for any attachments that were included in deleted message
    # These will likely become invalid, but it's nice to note them anyway
    if message.attachments != []:
        for item in message.attachments:
            # Break into seperate parts if we're going to cross character limit
            if len(mes) + len(item.url) > config.CHAR_LIMIT:
                await chan.send(mes)
                mes = item.url
            else:
                mes += '\n' + item.url
    await chan.send(mes)

"""
Should Log

Whether the bot should log this event in config.SYS_LOG
"""
def should_log(server):
    return not dbg.is_debug_bot() and server.id == config.HOME_SERVER

"""
On Ready

Occurs when Discord bot is first brought online
"""
@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)

    # Set Bouncer's activity status
    activity_object = discord.Activity(name="for your reports!", type=discord.ActivityType.watching)
    await client.change_presence(activity=activity_object)

"""
On Member Update

Occurs when a user updates an attribute (nickname, roles)
"""
@client.event
async def on_member_update(before, after):
    if not should_log(before.guild):
        return

    # If nickname has changed
    if before.nick != after.nick:
        # If they don't have an ending nickname, they reset to their actual username
        if after.nick == None:
            mes = f"**:spy: {str(after)}** has reset their username"
        else:
            new = after.nick
            mes = f"**:spy: {str(after)}** is now known as `{after.nick}`"
        chan = client.get_channel(config.SYS_LOG)
        await chan.send(mes)
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

        chan = client.get_channel(config.SYS_LOG)
        if mes != "":
            await chan.send(mes)

"""
On Member Ban

Occurs when a user is banned
"""
@client.event
async def on_member_ban(server, member):
    if not should_log(server):
        return

    # We can remove banned user from our answering machine and watch list (if they exist)
    commands.am.remove_entry(member.id)
    watch.remove_user(member.id)

    # Keep a record of their banning, in case the log is made after they're no longer here
    username = f"{str(member)}"
    commands.ul.add_ban(member.id, username)
    mes = f":newspaper2: **{username} ({member.id})** has been banned."
    chan = client.get_channel(config.SYS_LOG)
    await chan.send(mes)

"""
On Member Remove

Occurs when a user leaves the server
"""
@client.event
async def on_member_remove(member):
    if not should_log(member.guild):
        return

    # We can remove left users from our answering machine
    commands.am.remove_entry(member.id)
    watch.remove_user(member.id)

    # Remember that the user has left, in case we want to log after they're gone
    username = f"{str(member)}"
    commands.ul.add_ban(member.id, username)
    mes = f":wave: **{username} ({member.id})** has left"
    chan = client.get_channel(config.SYS_LOG)
    await chan.send(mes)

"""
On Message Delete

Occurs when a user's message is deleted
"""
@client.event
async def on_message_delete(message):
    if not should_log(message.guild) or message.author.bot:
        return

    await delete_message_helper(message)

"""
On Bulk Message Delete

Occurs when a user's messages are bulk deleted, such as ban or kick
"""
@client.event
async def on_bulk_message_delete(messages):
    if not should_log(messages[0].guild) or messages[0].author.bot:
        return

    for message in messages:
        await delete_message_helper(message)

"""
On Message Edit

Occurs when a user edits a message
"""
@client.event
async def on_message_edit(before, after):
    if not should_log(before.guild) or before.author.bot:
        return

    # Run edited message against censor.
    bad_message = await check_censor(after)
    if bad_message:
        return

    # Prevent embedding of content from triggering the log
    if before.content == after.content:
        return

    try:
        chan = client.get_channel(config.SYS_LOG)
        mes = f":pencil: **{str(before.author)}** modified in <#{before.channel.id}>: `{before.content}`"

        # Break into seperate parts if we're going to cross character limit
        if len(mes) + len(after.content) > (config.CHAR_LIMIT + 5):
            await chan.send(mes)
            mes = ""

        mes += f" to `{after.content}`"
        await chan.send(mes)

        # If user is on watchlist, then post it there as well
        watching = watch.should_note(after.author.id)
        if watching:
            watchchan = client.get_channel(config.WATCHLIST_CHAN)
            await watchchan.send(mes)

    except discord.errors.HTTPException as e:
        print(f"Unknown error with editing message. This message was unable to post for this reason: {e}\n")

"""
On Member Join

Occurs when a user joins the server
"""
@client.event
async def on_member_join(member):
    if not should_log(member.guild):
        return

    mes = f":confetti_ball: **{str(member)} ({member.id})** has joined"
    chan = client.get_channel(config.SYS_LOG)
    await chan.send(mes)

"""
On Voice State Update

Occurs when a user joins/leaves an audio channel
"""
@client.event
async def on_voice_state_update(member, before, after):
    if not should_log(member.guild) or member.bot:
        return

    if after.channel == None:
        mes = f":mute: **{str(member)}** has left voice channel {before.channel.name}"
        chan = client.get_channel(config.SYS_LOG)
        await chan.send(mes)
    elif before.channel == None:
        mes = f":loud_sound: **{str(member)}** has joined voice channel {after.channel.name}"
        chan = client.get_channel(config.SYS_LOG)
        await chan.send(mes)

"""
On Message

Occurs when a user posts a message
More or less the main function
"""
@client.event
async def on_message(message):
    # Bouncer should not react to its own messages
    if message.author.id == client.user.id:
        return

    try:
        # Allows the owner to enable debug mode
        if dbg.check_toggle(message):
            await dbg.toggle_debug(message)
            return

        if dbg.should_ignore_message(message):
            return

        # If bouncer detects a private DM sent to it
        if type(message.channel) is discord.channel.DMChannel:
            # Store who the most recent user was, for $reply ^
            commands.am.set_recent_reply(message.author)

            content = commonbot.utils.combineMessage(message)
            mes = f"**{str(message.author)}** (ID: {message.author.id}): {content}"

            # If not blocked, send message along to specified mod channel
            if not commands.bu.is_in_blocklist(message.author.id):
                chan = None
                # If we share the main server, treat that as a DM
                if config.HOME_SERVER in [x.id for x in message.author.mutual_guilds]:
                    chan = client.get_channel(config.MAILBOX)
                # The only other server we should share is the ban appeal server
                else:
                    chan = client.get_channel(config.BAN_APPEAL)

                logMes = await chan.send(mes)

                # Send them a message so they know something actually happened
                await message.channel.send("Your message has been forwarded!")

                # Lets also add/update them in answering machine
                mes_entry = AnsweringMachineEntry(f"{str(message.author)}", message.created_at, content, logMes.jump_url)
                commands.am.update_entry(message.author.id, mes_entry)
            return

        # Run message against censor
        bad_message = await check_censor(message)
        if bad_message:
            return

        # Check if user is on watchlist, and should be tracked
        watching = watch.should_note(message.author.id)
        if watching:
            chan = client.get_channel(config.WATCHLIST_CHAN)
            content = commonbot.utils.combineMessage(message)
            mes = f"**{str(message.author)}** (ID: {message.author.id}) said in <#{message.channel.id}>: {content}"
            await chan.send(mes)

        # If a user pings bouncer, log into mod channel
        if client.user in message.mentions:
            content = commonbot.utils.combineMessage(message)
            mes = f"**{str(message.author)}** (ID: {message.author.id}) pinged me in <#{message.channel.id}>: {content}\n{message.jump_url}"
            chan = client.get_channel(config.MAILBOX)
            await chan.send(mes)

        # Functions in this category are those where we care that the user has the correct roles, but don't care about which channel they're invoked in
        elif commonbot.utils.checkRoles(message.author, config.VALID_ROLES) and message.channel.id in config.VALID_INPUT_CHANS:
            if message.content.startswith(config.CMD_PREFIX):
                cmd = commonbot.utils.strip_prefix(message.content, config.CMD_PREFIX)
                cmd = commonbot.utils.get_first_word(cmd)
                if cmd in FUNC_DICT:
                    func = FUNC_DICT[cmd][0]
                    arg = FUNC_DICT[cmd][1]
                    await func(message, arg)
    except discord.errors.Forbidden as e:
        if e.code == 50007:
            chan = client.get_channel(config.MAILBOX)
            logMes = await chan.send("Unable to send message - Can't send messages to that user")
        else:
            print(traceback.format_exc())
            pass
    except discord.errors.HTTPException as e:
        print(traceback.format_exc())
        pass

client.run(config.DISCORD_KEY)
