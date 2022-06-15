import discord
from dataclasses import dataclass
from datetime import datetime, timezone
from commonbot.utils import get_time_delta
from typing import Optional

@dataclass
class AnsweringMachineEntry:
    name: str
    timestamp: datetime
    last_message: str
    message_url: str

class AnsweringMachine:
    def __init__(self):
        self.waiting_list = {}
        self.recent_reply = None

    def set_recent_reply(self, user: discord.Member):
        self.recent_reply = user

    def get_recent_reply(self) -> Optional[discord.Member]:
        return self.recent_reply

    def recent_reply_exists(self) -> bool:
        return self.recent_reply != None

    def remove_entry(self, user_id: int):
        if user_id in self.waiting_list:
            del self.waiting_list[user_id]

    def get_entries(self) -> dict[int, discord.Member]:
        return self.waiting_list

    def update_entry(self, user_id: int, user_entry: discord.Member):
        self.waiting_list[user_id] = user_entry

    async def clear_entries(self, message: discord.Message, _):
        self.waiting_list.clear()
        await message.channel.send("Waiting queue has been cleared")

    async def gen_waiting_list(self, message: discord.Message, _):
        curr_time = datetime.now(timezone.utc)
        # Assume there are no messages in the queue
        found = False

        waiting_list = self.get_entries().copy()
        for key, item in waiting_list.items():
            days, hours, minutes, seconds = get_time_delta(curr_time, item.timestamp)
            # Purge items that are older than one day
            if days > 0:
                self.remove_entry(key)
            else:
                found = True
                out = f"{item.name} ({key}) said `{item.last_message}` | {hours}h{minutes}m ago\n{item.message_url}\n"
                await message.channel.send(out)

        if not found:
            await message.channel.send("There are no users awaiting replies")
