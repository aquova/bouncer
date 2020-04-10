import sqlite3
from config import DATABASE_PATH

class BlockedUsers:
    def __init__(self):
        self.blocklist = []

    def populate_blocklist(self):
        sqlconn = sqlite3.connect(DATABASE_PATH)
        blockDB = sqlconn.execute("SELECT * FROM blocks").fetchall()
        self.blocklist = [x[0] for x in blockDB]
        sqlconn.close()

    def block_user(self, userid):
        sqlconn = sqlite3.connect(DATABASE_PATH)
        sqlconn.execute("INSERT INTO blocks (id) VALUES (?)", [userid])
        sqlconn.commit()
        sqlconn.close()

        self.blocklist.append(userid)

    def unblock_user(self, userid):
        sqlconn = sqlite3.connect(DATABASE_PATH)
        sqlconn.execute("DELETE FROM blocks WHERE id=?", [userid])
        sqlconn.commit()
        sqlconn.close()

        self.blocklist.remove(userid)

    def is_in_blocklist(self, userid):
        return userid in self.blocklist
