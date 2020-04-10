import datetime, sqlite3
from dataclasses import dataclass
from config import DATABASE_PATH, LogTypes
from Utils import formatTime

@dataclass
class UserLogEntry:
    user_id: int
    name: str
    log_type: int
    timestamp: datetime
    log_message: str
    staff: str
    message_url: str

    def __str__(self):
        logWord = ""
        if self.log_type == LogTypes.BAN:
            logWord = "Banned"
        elif self.log_type == LogTypes.NOTE:
            logWord = "Note"
        elif self.log_type == LogTypes.KICK:
            logWord = "Kicked"
        elif self.log_type == LogTypes.UNBAN:
            logWord = "Unbanned"
        else: # LogTypes.WARN
            logWord = "Warning #{}".format(self.log_type)

        return "[{date}] **{name}** - {word} by {staff} - {message}\n".format(
            date = formatTime(self.timestamp),
            name = self.name,
            word = logWord,
            staff = self.staff,
            message = self.log_message
        )

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

def fetch_id_by_username(username):
    sqlconn = sqlite3.connect(DATABASE_PATH)
    searchResults = sqlconn.execute("SELECT id FROM badeggs WHERE username=?", [username]).fetchall()
    sqlconn.close()

    if searchResults != []:
        return searchResults[0][0]
    else:
        return None

def get_warn_count(userid):
    sqlconn = sqlite3.connect(DATABASE_PATH)
    searchResults = sqlconn.execute("SELECT COUNT(*) FROM badeggs WHERE id=? AND num > 0", [userid]).fetchone()
    sqlconn.close()

    return searchResults[0] + 1

def get_note_count(userid):
    sqlconn = sqlite3.connect(DATABASE_PATH)
    searchResults = sqlconn.execute("SELECT COUNT(*) FROM badeggs WHERE id=? AND num = -1", [userid]).fetchone()
    sqlconn.close()

    return searchResults[0] + 1

def remove_log(dbid):
    sqlconn = sqlite3.connect(DATABASE_PATH)
    sqlconn.execute("REPLACE INTO badeggs (dbid, id, username, num, date, message, staff, post) VALUES (?, NULL, NULL, NULL, NULL, NULL, NULL, NULL)", [dbid])
    sqlconn.commit()
    sqlconn.close()

def clear_user_logs(userid):
    logs = search(userid)
    for log in logs:
        remove_log(log[0])
