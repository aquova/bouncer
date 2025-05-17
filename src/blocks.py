import discord

import db

class BlockedUsers:
    def __init__(self):
        block_db = db.get_blocklist()
        self.blocklist: list[int] = [int(x[0]) for x in block_db] # TODO: We really should be storing these as INT, not TEXT

    def handle_block(self, user: discord.User, block: bool) -> str:
        is_blocked = self.is_in_blocklist(user.id)
        if block:
            if is_blocked:
                return "Um... That user was already blocked..."
            else:
                self._block_user(user.id)
                return f"I have now blocked {str(user)}. Their DMs will no longer be forwarded."
        else:
            if not is_blocked:
                return "That user hasn't been blocked..."
            else:
                self._unblock_user(user.id)
                return f"I have now unblocked {str(user)}. Their DMs will now be forwarded."

    def _block_user(self, userid: int):
        db.add_block(userid)
        self.blocklist.append(userid)

    def _unblock_user(self, userid: int):
        db.remove_block(userid)
        self.blocklist.remove(userid)

    def is_in_blocklist(self, userid: int) -> bool:
        return userid in self.blocklist
