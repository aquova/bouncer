import datetime, discord
from dataclasses import dataclass
from utils import getTimeDelta

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

    def set_recent_reply(self, user):
        self.recent_reply = user

    def get_recent_reply(self):
        return self.recent_reply

    def recent_reply_exists(self):
        return self.recent_reply != None

    def remove_entry(self, user_id):
        if user_id in self.waiting_list:
            del self.waiting_list[user_id]

    def get_entries(self):
        return self.waiting_list

    def update_entry(self, user_id, user_entry):
        self.waiting_list[user_id] = user_entry

    async def clear_entries(self, message, _):
        self.waiting_list.clear()
        await message.channel.send("Waiting queue has been cleared")

    async def gen_waiting_list(self, message, _):
        curr_time = datetime.datetime.utcnow()
        first = True
        # Assume there are no messages in the queue
        out = "There are no users awaiting replies."

        waiting_list = self.get_entries().copy()
        for key, item in waiting_list.items():
            days, hours, minutes = getTimeDelta(curr_time, item.timestamp)
            # Purge items that are older than one day
            if days > 0:
                self.remove_entry(key)
            else:
                # If we find a message, change the printout message
                if first:
                    out = "Users who are still awaiting replies:\n"
                    first = False

                out += "{} ({}) said `{}` | {}h{}m ago\n{}\n".format(item.name, key, item.last_message, hours, minutes, item.message_url)

        await message.channel.send(out)
