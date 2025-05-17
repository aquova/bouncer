from dataclasses import dataclass
from datetime import datetime, timezone

import discord

from utils import get_time_delta
from config import HOME_SERVER


@dataclass
class AnsweringMachineEntry:
    name: str
    timestamp: datetime
    last_message: str
    message_url: str | None

class AnsweringMachine:
    def __init__(self):
        self.waiting_list: dict[int, AnsweringMachineEntry] = {}

    def remove_entry(self, user_id: int):
        if user_id in self.waiting_list:
            del self.waiting_list[user_id]

    def get_entries(self) -> dict[int, AnsweringMachineEntry]:
        return self.waiting_list

    def update_entry(self, user_id: int, user_entry: AnsweringMachineEntry):
        self.waiting_list[user_id] = user_entry

    def clear_entries(self):
        self.waiting_list.clear()

    def list_waiting(self) -> str:
        waiting = self._gen_waiting_list()
        if len(waiting) == 0:
            return "There are no messages waiting!"
        return "\n".join(waiting)

    def _gen_waiting_list(self) -> list[str]:
        curr_time = datetime.now(timezone.utc)
        waiting_list = self.get_entries().copy()
        output_list: list[str] = []
        for key, item in waiting_list.items():
            days, hours, minutes, _ = get_time_delta(curr_time, item.timestamp)
            # Purge items that are older than one day
            if days > 0:
                self.remove_entry(key)
            else:
                out = f"{item.name} ({key}) said `{item.last_message}` | {hours}h{minutes}m ago\n{item.message_url}\n"
                output_list.append(out)
        return output_list

def is_in_home_server(author: discord.Member | discord.User) -> bool:
    return HOME_SERVER in [x.id for x in author.mutual_guilds]

