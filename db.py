import datetime, sqlite3
from dataclasses import dataclass
from config import DATABASE_PATH

@dataclass
class UserLogEntry:
    user_id: int
    name: str
    log_type: int
    timestamp: datetime
    log_message: str
    staff: str
    message_url: str

def initialize():
    sqlconn = sqlite3.connect(DATABASE_PATH)
    sqlconn.execute("CREATE TABLE IF NOT EXISTS badeggs (dbid INT PRIMARY KEY, id INT, username TEXT, num INT, date DATE, message TEXT, staff TEXT, post INT);")
    sqlconn.execute("CREATE TABLE IF NOT EXISTS blocks (id TEXT);")
    sqlconn.execute("CREATE TABLE IF NOT EXISTS staffLogs (staff TEXT PRIMARY KEY, bans INT, warns INT);")
    sqlconn.execute("CREATE TABLE IF NOT EXISTS monthLogs (month TEXT PRIMARY KEY, bans INT, warns INT);")
    sqlconn.commit()
    sqlconn.close()

def search(user_id):
    sqlconn = sqlite3.connect(DATABASE_PATH)
    searchResults = sqlconn.execute("SELECT dbid, id, username, num, date, message, staff, post FROM badeggs WHERE id=?", [user_id]).fetchall()
    sqlconn.close()

    return searchResults
