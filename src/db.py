import datetime, sqlite3
from dataclasses import dataclass
from config import DATABASE_PATH, LogTypes
from utils import formatTime

@dataclass
class UserLogEntry:
    dbid: int
    user_id: int
    name: str
    log_type: int
    timestamp: datetime
    log_message: str
    staff: str
    message_url: str

    def __str__(self):
        logWord = ""
        if self.log_type == LogTypes.BAN.value:
            logWord = "Banned"
        elif self.log_type == LogTypes.NOTE.value:
            logWord = "Note"
        elif self.log_type == LogTypes.KICK.value:
            logWord = "Kicked"
        elif self.log_type == LogTypes.UNBAN.value:
            logWord = "Unbanned"
        else: # LogTypes.WARN
            logWord = f"Warning #{self.log_type}"

        return f"[{formatTime(self.timestamp)}] **{self.name}** - {logWord} by {self.staff} - {self.log_message}\n"

    def as_list(self):
        return [
            self.dbid,
            self.user_id,
            self.name,
            self.log_type,
            self.timestamp,
            self.log_message,
            self.staff,
            self.message_url
        ]

def initialize():
    sqlconn = sqlite3.connect(DATABASE_PATH)
    sqlconn.execute("CREATE TABLE IF NOT EXISTS badeggs (dbid INT PRIMARY KEY, id INT, username TEXT, num INT, date DATE, message TEXT, staff TEXT, post INT);")
    sqlconn.execute("CREATE TABLE IF NOT EXISTS blocks (id TEXT);")
    sqlconn.execute("CREATE TABLE IF NOT EXISTS staffLogs (staff TEXT PRIMARY KEY, bans INT, warns INT);")
    sqlconn.execute("CREATE TABLE IF NOT EXISTS monthLogs (month TEXT PRIMARY KEY, bans INT, warns INT);")
    sqlconn.execute("CREATE TABLE IF NOT EXISTS watching (id INT PRIMARY KEY);")
    sqlconn.commit()
    sqlconn.close()

def search(user_id):
    sqlconn = sqlite3.connect(DATABASE_PATH)
    search_results = sqlconn.execute("SELECT dbid, id, username, num, date, message, staff, post FROM badeggs WHERE id=?", [user_id]).fetchall()
    sqlconn.close()

    entries = []
    for result in search_results:
        entry = UserLogEntry(result[0], result[1], result[2], result[3], result[4], result[5], result[6], result[7])
        entries.append(entry)

    return entries

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

def add_log(log_entry):
    sqlconn = sqlite3.connect(DATABASE_PATH)
    sqlconn.execute("INSERT OR REPLACE INTO badeggs (dbid, id, username, num, date, message, staff, post) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", log_entry.as_list())
    sqlconn.commit()
    sqlconn.close()

def remove_log(dbid):
    sqlconn = sqlite3.connect(DATABASE_PATH)
    sqlconn.execute("REPLACE INTO badeggs (dbid, id, username, num, date, message, staff, post) VALUES (?, NULL, NULL, NULL, NULL, NULL, NULL, NULL)", [dbid])
    sqlconn.commit()
    sqlconn.close()

def clear_user_logs(userid):
    logs = search(userid)
    for log in logs:
        remove_log(log.dbid)

def get_dbid():
    sqlconn = sqlite3.connect(DATABASE_PATH)
    globalcount = sqlconn.execute("SELECT COUNT(*) FROM badeggs").fetchone()
    sqlconn.close()

    return globalcount[0]

def get_watch_list():
    sqlconn = sqlite3.connect(DATABASE_PATH)
    results = sqlconn.execute("SELECT * FROM watching").fetchall()
    sqlconn.close()

    return results

def add_watch(userid):
    sqlconn = sqlite3.connect(DATABASE_PATH)
    sqlconn.execute("INSERT OR REPLACE INTO watching (id) VALUES (?)", [userid])
    sqlconn.commit()
    sqlconn.close()

def del_watch(userid):
    sqlconn = sqlite3.connect(DATABASE_PATH)
    sqlconn.execute("DELETE FROM watching WHERE id=?", [userid])
    sqlconn.commit()
    sqlconn.close()
