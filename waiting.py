import datetime
from dataclasses import dataclass

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
