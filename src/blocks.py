import db

class BlockedUsers:
    def __init__(self):
        self.populate_blocklist()

    def populate_blocklist(self):
        blockDB = db.get_blocklist()
        self.blocklist = [x[0] for x in blockDB]

    def block_user(self, userid: int):
        db.add_block(userid)
        self.blocklist.append(userid)

    def unblock_user(self, userid: int):
        db.remove_block(userid)
        self.blocklist.remove(userid)

    def is_in_blocklist(self, userid: int) -> bool:
        return userid in self.blocklist
