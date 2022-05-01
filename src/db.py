import sqlite3
from dataclasses import dataclass
from config import DATABASE_PATH, LogTypes
from commonbot.utils import format_time
from datetime import datetime, timezone
from typing import Optional

@dataclass
class UserLogEntry:
    dbid: int
    user_id: int
    name: str
    log_type: int
    timestamp: datetime
    log_message: str
    staff: str
    message_id: Optional[int]

    def __str__(self):
        logWord = ""
        if self.log_type == LogTypes.BAN.value or self.log_type == LogTypes.SCAM.value:
            logWord = "Banned"
        elif self.log_type == LogTypes.NOTE.value:
            logWord = "Note"
        elif self.log_type == LogTypes.KICK.value:
            logWord = "Kicked"
        elif self.log_type == LogTypes.UNBAN.value:
            logWord = "Unbanned"
        else: # LogTypes.WARN
            logWord = f"Warning #{self.log_type}"

        return f"[{format_time(self.timestamp)}] **{self.name}** - {logWord} by {self.staff} - {self.log_message}\n"

    def as_list(self):
        return [
            self.dbid,
            self.user_id,
            self.name,
            self.log_type,
            self.timestamp,
            self.log_message,
            self.staff,
            self.message_id
        ]

"""
Initialize database

Generates database with needed tables if it doesn't exist
"""
def initialize():
    sqlconn = sqlite3.connect(DATABASE_PATH)
    sqlconn.execute("CREATE TABLE IF NOT EXISTS badeggs (dbid INT PRIMARY KEY, id INT, username TEXT, num INT, date DATE, message TEXT, staff TEXT, post INT);")
    sqlconn.execute("CREATE TABLE IF NOT EXISTS blocks (id TEXT);")
    sqlconn.execute("CREATE TABLE IF NOT EXISTS staffLogs (staff TEXT PRIMARY KEY, bans INT, warns INT);")
    sqlconn.execute("CREATE TABLE IF NOT EXISTS monthLogs (month TEXT PRIMARY KEY, bans INT, warns INT);")
    sqlconn.execute("CREATE TABLE IF NOT EXISTS watching (id INT PRIMARY KEY);")
    sqlconn.execute("CREATE TABLE IF NOT EXISTS censored (id INT PRIMARY KEY, logs INT, last DATE);")
    sqlconn.commit()
    sqlconn.close()

def _db_read(query: tuple) -> list[tuple]:
    sqlconn = sqlite3.connect(DATABASE_PATH)
    # The * operator in Python expands a tuple into function params
    results = sqlconn.execute(*query).fetchall()
    sqlconn.close()

    return results

def _db_write(query: tuple[str, list]):
    sqlconn = sqlite3.connect(DATABASE_PATH)
    sqlconn.execute(*query)
    sqlconn.commit()
    sqlconn.close()

def search(user_id: int) -> list[UserLogEntry]:
    query = ("SELECT dbid, id, username, num, date, message, staff, post FROM badeggs WHERE id=?", [user_id])
    search_results = _db_read(query)

    entries = []
    for result in search_results:
        entry = UserLogEntry(result[0], result[1], result[2], result[3], result[4], result[5], result[6], result[7])
        entries.append(entry)

    return entries

def fetch_id_by_username(username: str) -> Optional[str]:
    query = ("SELECT id FROM badeggs WHERE username=?", [username])
    searchResults = _db_read(query)

    if searchResults != []:
        return searchResults[0][0]
    else:
        return None

def get_warn_count(userid: int) -> int:
    query = ("SELECT COUNT(*) FROM badeggs WHERE id=? AND num > 0", [userid])
    searchResults = _db_read(query)

    return searchResults[0][0] + 1

def get_note_count(userid: int) -> int:
    query = ("SELECT COUNT(*) FROM badeggs WHERE id=? AND num = -1", [userid])
    searchResults = _db_read(query)

    return searchResults[0][0] + 1

def add_log(log_entry: UserLogEntry):
    query = ("INSERT OR REPLACE INTO badeggs (dbid, id, username, num, date, message, staff, post) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", log_entry.as_list())
    _db_write(query)

def remove_log(dbid: int):
    query = ("REPLACE INTO badeggs (dbid, id, username, num, date, message, staff, post) VALUES (?, NULL, NULL, NULL, NULL, NULL, NULL, NULL)", [dbid])
    _db_write(query)

def clear_user_logs(userid: int):
    logs = search(userid)
    for log in logs:
        remove_log(log.dbid)

def get_censor_count(userid: int) -> Optional[tuple[int, datetime]]:
    query = ("SELECT * FROM censored WHERE id=?", [userid])
    searchResults = _db_read(query)
    if searchResults != []:
        return (searchResults[0][1], searchResults[0][2])
    else:
        return None

def add_censor_count(userid: int):
    read_query = ("SELECT logs FROM censored WHERE id=?", [userid])
    searchResults = _db_read(read_query)
    num_censors = 1
    if searchResults != []:
        num_censors = searchResults[0][0] + 1

    write_query = ("INSERT OR REPLACE INTO censored (id, logs, last) VALUES (?, ?, ?)", [userid, num_censors, datetime.now(timezone.utc)])
    _db_write(write_query)

def get_dbid() -> int:
    query = ("SELECT COUNT(*) FROM badeggs",)
    globalcount = _db_read(query)

    return globalcount[0][0]

def get_watch_list() -> list[tuple]:
    query = ("SELECT * FROM watching",)
    return _db_read(query)

def add_watch(userid: int):
    query = ("INSERT OR REPLACE INTO watching (id) VALUES (?)", [userid])
    _db_write(query)

def del_watch(userid: int):
    query = ("DELETE FROM watching WHERE id=?", [userid])
    _db_write(query)

def get_staffdata(staff: str) -> list[tuple]:
    if not staff:
        query = ("SELECT * FROM staffLogs",)
        return _db_read(query)
    else:
        squery = ("SELECT * FROM staffLogs WHERE staff=?", [staff])
        return _db_read(squery)

def add_staffdata(staff: str, bans: int, warns: int, is_replace: bool):
    if is_replace:
        query = ("REPLACE INTO staffLogs (staff, bans, warns) VALUES (?, ?, ?)", [staff, bans, warns])
    else:
        query = ("INSERT INTO staffLogs (staff, bans, warns) VALUES (?, ?, ?)", [staff, bans, warns])

    _db_write(query)

def get_monthdata(month: str) -> list[tuple]:
    if not month:
        query = ("SELECT * FROM monthLogs",)
        return _db_read(query)
    else:
        mquery = ("SELECT * FROM monthLogs WHERE month=?", [month])
        return _db_read(mquery)

def add_monthdata(month: str, bans: int, warns: int, is_replace: bool):
    if is_replace:
        query = ("REPLACE INTO monthLogs (month, bans, warns) VALUES (?, ?, ?)", [month, bans, warns])
    else:
        query = ("INSERT INTO monthLogs (month, bans, warns) VALUES (?, ?, ?)", [month, bans, warns])

    _db_write(query)

def get_blocklist() -> list[tuple]:
    query = ("SELECT * FROM blocks",)
    return _db_read(query)

def add_block(userid: int):
    query = ("INSERT INTO blocks (id) VALUES (?)", [userid])
    _db_write(query)

def remove_block(userid: int):
    query = ("DELETE FROM blocks WHERE ID=?", [userid])
    _db_write(query)
