from collections import OrderedDict
from threading import Lock
from typing import cast

import discord

from singletons import singletons
import db
from config import HOME_SERVER, THREAD_ROLES
from waiting import AnsweringMachineEntry, is_in_home_server
import utils

# TODO: This is temporary until support for Forwarded messages comes in the next version of discord.py
FORWARD_FLAG_VAL = 16384

class MessageForwarder:
    """
    Handles message forwarding between bouncer DMs and server staff.

    There are two key parts of this functionality:
     - Bouncer receives DM -> forward it to staff
     - Staff replies to forwarded message -> reply to user in DMS

    The first part is here. For the second part, the reply command handles figuring out who to message and sending the message.

    We could move reply command functionality into this class, but I left it as is.
    """
    def __init__(self):
        """
        Creates a new message forwarder.
        """
        # Maps user ids to reply thread ids - used when receiving a DM to know which thread to forward it to
        self._user_id_to_thread_id = LRUCache(lambda user_id: db.get_user_reply_thread_id(user_id), maxsize=50)

        # Maps user reply thread ids to user ids - used when staff replies in a thread to know which user to send the reply to
        self._thread_id_to_user_id = LRUCache(lambda thread_id: db.get_user_reply_thread_user_id(thread_id), maxsize=50)

        # Both of the above use an LRU cache wrapper around accessing the DB so that every DM/reply does not trigger DB access
        # The chosen cache size should be equal to the number of concurrent/active conversations we expect users to have with bouncer

    async def on_dm(self, client: discord.Client, message: discord.Message, edit: bool = False):
        """
        On a DM, forward the message to staff.

        :param message: The message that was sent.
        :param edit: Whether this message was an edit
        """
        # Ignore blocked users
        if singletons.blocks.is_in_blocklist(message.author.id):
            return

        # Throw a warning about sending forwarded messages to the bot
        # TODO: This should be removed when discord.py updates
        if message.flags.value == FORWARD_FLAG_VAL:
            await message.channel.send("Sorry, the bot cannot handle Forwarded messages. Perhaps try sending a link to the message?")
            return

        # If the user is in the home server, treat it as a regular DM
        # Otherwise, assume it's a ban appeal (users must have a mutual server to message bouncer, they should only be able to join those two)
        is_ban_appeal = not is_in_home_server(message.author)

        # If it's not a ban appeal they can be pinged b/c they're in the server where we're forwarding the message
        # Otherwise they can't, so we show username details instead
        reply_message = f"<@{message.author.id}>" if not is_ban_appeal else f"{str(message.author)} ({message.author.id})"

        # Handle ban appeals
        if is_ban_appeal:
            reply_message += " (banned)"

        if edit:
            reply_message += " (edited)"

        # Fill in the rest of the message with what the user said
        content = utils.combine_message(message)
        reply_message += f": {content}"

        # Get or create the appropriate thread for the message user
        reply_channel = await self.get_or_create_user_reply_thread(client, message.author, True, content=content)

        # Forward the message to the channel/thread
        log_mes = await utils.send_message(reply_message, reply_channel)

        try:
            # Send the user a message so they know something actually happened
            if not edit:
                await message.add_reaction("📨")
        except discord.errors.Forbidden as err:
            if err.code == 50007:
                await reply_channel.send("Unable to send message forward notification to the above user - Can't send messages to that user")
            else:
                await reply_channel.send(f"ERROR: While attempting to send message forward notification, there was an unexpected error: {err}")

        # Record that the user is waiting for a reply
        url = log_mes.jump_url if log_mes else None
        mes_entry = AnsweringMachineEntry(str(message.author), message.created_at, content, url)
        singletons.am.update_entry(message.author.id, mes_entry)

    def get_userid_for_user_reply_thread(self, channel_id: int) -> int | None:
        """
        Get the user id to reply to if message was sent in a reply thread.

        :param message: The staff reply message.
        :return: The user id, if message was sent in a user reply thread. None otherwise.
        """
        return self._thread_id_to_user_id(channel_id)

    def get_reply_thread_id_for_user(self, user: discord.User | discord.Member) -> int | None:
        """
        Get the reply thread id for a user.

        :param user: The user to get the reply thread id for.
        :return: The reply thread id, or None if the reply thread doesn't exist.
        """
        return self._user_id_to_thread_id(user.id)

    async def get_or_create_user_reply_thread(self, client: discord.Client, user: discord.User | discord.Member, from_user_message: bool=False, content: str | None=None) -> discord.Thread:
        """
        Either retrieves the existing reply thread for a user, or creates a new one if they don't have one.

        :param user: The user to get or create the reply thread for.
        :param from_user_message: Whether user reply thread retrieval is motivated by the user sending bouncer a message (True) or staff moderation (False).
        :return: The existing/new thread.
        """
        thread_id = self._user_id_to_thread_id(user.id)

        if thread_id is None:
            # This is a first time user messaging bouncer or staff moderating a user -> create a reply thread for them
            return await self._create_reply_thread(client, user, singletons.mailbox)

        # Get thread from thread cache (holds active threads only)
        user_reply_thread = client.get_channel(thread_id)
        if user_reply_thread is not None and isinstance(user_reply_thread, discord.Thread):
            # Active thread -> update it and use it for the conversation
            await self._update_reply_thread(client, user, user_reply_thread)
            return user_reply_thread

        # The thread is either archived or deleted; use fetch channel to find out which
        # The order is important: fetch channel is an API call, so we want to avoid it if possible
        try:
            user_reply_thread = cast(discord.Thread, await client.fetch_channel(thread_id))

            if from_user_message:
                embed: discord.Embed = discord.Embed(
                    title=f"\N{ENVELOPE} Mail from {user.global_name or user}",
                    description=f"{content if len(content) <= 99 else content[:99] + '…'}" if content else None,
                    colour=discord.Colour.blue(),
                    url=user_reply_thread.jump_url)
                await singletons.mailbox.send(embed=embed)
            else:
                # It was archived -> send a message to notify mods someone is starting a new conversation or that there was moderation activity
                msg: str = f"New moderation activity for {user.mention}\nTheir reply thread has been un-archived: {user_reply_thread.mention}"
                await singletons.mailbox.send(content=msg)
            await self._update_reply_thread(client, user, user_reply_thread)
            return user_reply_thread
        except discord.errors.NotFound:
            # It was deleted
            await singletons.mailbox.send(f"Reply thread for user {user.mention} was not found (it was probably deleted), creating a new one.")
            return await self._create_reply_thread(client, user, singletons.mailbox)

    async def _create_reply_thread(self, client: discord.Client, user: discord.User | discord.Member, parent_channel: discord.TextChannel) -> discord.Thread:
        """
        Creates a reply thread for a user.

        :param user: The user to crate the reply thread for.
        :param parent_channel: The channel to create the thread in.
        :return: The new thread.
        """
        thread = await parent_channel.create_thread(name=self._user_reply_thread_name(client, user), type=discord.ChannelType.public_thread)

        # Update DB and caches
        db.set_user_reply_thread(user.id, thread.id)
        self._user_id_to_thread_id.set(thread.id, user.id)
        self._thread_id_to_user_id.set(user.id, thread.id)

        # Add staff to the thread
        await self._add_staff_to_thread(thread)

        return thread

    async def _add_staff_to_thread(self, thread: discord.Thread):
        """
        Adds all staff members to a thread.

        :param thread: The thread to add staff to.
        """
        content = "This is a mention to add staff to this thread: "

        message = await thread.send(content)

        content += ', '.join([f"<@&{role_id}>" for role_id in THREAD_ROLES])

        # By editing in a mention, we add staff to the thread without pinging them
        await message.edit(content=content)

    async def _update_reply_thread(self, client: discord.Client, user: discord.User | discord.Member, thread: discord.Thread):
        """
        Update a reply thread for a user. That means:
          - change the thread name to match the user's current name
          - un-archive it

        :param user: The user the thread is for.
        :param thread: The thread.
        """
        thread_name = self._user_reply_thread_name(client, user)

        if thread.name != thread_name or thread.archived:
            await thread.edit(name=thread_name, archived=False)
            await self._add_staff_to_thread(thread)

    def _user_reply_thread_name(self, client: discord.Client, user: discord.User | discord.Member) -> str:
        """
        Returns the name of a user reply thread for a user.

        :param user: The user to create the thread name for.
        :return: The thread name.
        """
        # Try to get their SDV nickname (will be None if they're not in the SDV server, or not in the member cache) for a nicer thread name
        home_guild = client.get_guild(HOME_SERVER)
        if home_guild is not None:
            member = home_guild.get_member(user.id)
            if member is not None:
                return f"{member.display_name} ({str(user)})"

        # If that didn't work, use their non-SDV name
        return str(user)


class LRUCache:
    """
    A custom LRU cache (https://en.wikipedia.org/wiki/Cache_replacement_policies#Least_recently_used_(LRU)).
    Differs from stdlib's functools.lru_cache in that it allows bypassing func to set values directly.

    Based on this comment: https://bugs.python.org/issue28178#msg276812.
    """
    def __init__(self, func, maxsize=128):
        """
        Creates a new instance.

        :param func: The function to call to get the value for a key if not present in the cache.
        :param maxsize: The maximum number of items to hold before evicting entries.
        """
        self._cache = OrderedDict()
        self._lock = Lock()
        self._func = func
        self._maxsize = maxsize

    def __call__(self, *args):
        """
        Retrieve the value for the given key (args).

        :param args: The key.
        :return:
        """
        with self._lock:
            # If in cache: set entry as recently used, and return it
            if args in self._cache:
                self._cache.move_to_end(args)
                return self._cache[args]

            # Not in cache: call function to get result, store in cache (this also sets the entry as recently used)
            result = self._func(*args)
            self._cache[args] = result

            # Evict the oldest entry if reached max cache size
            if len(self._cache) > self._maxsize:
                self._cache.popitem(last=False)

            return result

    def set(self, result, *args):
        """
        Set the result for given args, bypassing func.

        :param result: The result value.
        :param args: The args that would be provided to func.
        """
        with self._lock:
            self._cache[args] = result
            self._cache.move_to_end(args)
            if len(self._cache) > self._maxsize:
                self._cache.popitem(last=False)

    def debug_print(self):
        print(self._cache)


message_forwarder = MessageForwarder()
