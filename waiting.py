import datetime
from dataclasses import dataclass
from Utils import getTimeDelta

@dataclass
class AnsweringMachineEntry:
    name: str
    timestamp: datetime
    last_message: str
    message_url: str

class AnsweringMachine:
    def __init__(self):
        self.waiting_list = {}

    def remove_entry(self, user_id):
        if user_id in self.waiting_list:
            del self.waiting_list[user_id]

    def get_entries(self):
        return self.waiting_list

    def update_entry(self, user_id, user_entry):
        self.waiting_list[user_id] = user_entry

    def clear_entries(self):
        self.waiting_list.clear()

    def gen_waiting_list(self):
        curr_time = datetime.datetime.utcnow()
        first = True
        # Assume there are no messages in the queue
        out = "There are no users awaiting replies."

        waiting_list = self.get_entries().items()
        for key, item in waiting_list:
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

        # We probably won't get enough messages for this to go over the 2000 char limit, but it is a possibility, so watch out.
        return out

