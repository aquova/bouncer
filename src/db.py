import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone

from config import DATABASE_PATH
from logtypes import LogTypes, past_tense
from utils import format_time


@dataclass
class UserLogEntry:
    dbid: int | None
    user_id: int
    log_type: LogTypes
    timestamp: datetime
    log_message: str
    staff: str
    message_id: int | None

    def format(self, warn_num: int | None=None):
        now = datetime.now(timezone.utc)
        diff = now - self.timestamp
        obsolete_tag = "**[OLD]**" if diff.days > 365 else ""
        return f"[{format_time(self.timestamp)}] {obsolete_tag} {self.log_word(warn_num)} by {self.staff} - {self.log_message}\n"

    def log_word(self, warn_num: int | None=None) -> str:
        if warn_num is not None:
            return f"Warning #{warn_num}"
        else:
            return past_tense(self.log_type)

"""
Initialize database

Generates database with needed tables if it doesn't exist
"""
def initialize():
    sqlconn = sqlite3.connect(DATABASE_PATH)
    sqlconn.execute("CREATE TABLE IF NOT EXISTS badeggs (dbid INTEGER PRIMARY KEY AUTOINCREMENT, id INTEGER, log INTEGER, date DATE, message TEXT, staff TEXT, post INTEGER);")
    sqlconn.execute("CREATE TABLE IF NOT EXISTS blocks (id TEXT);")
    sqlconn.execute("CREATE TABLE IF NOT EXISTS staffLogs (staff TEXT PRIMARY KEY, bans INT, warns INT);")
    sqlconn.execute("CREATE TABLE IF NOT EXISTS monthLogs (month TEXT PRIMARY KEY, bans INT, warns INT);")
    sqlconn.execute("CREATE TABLE IF NOT EXISTS watching (id INT PRIMARY KEY);")
    sqlconn.execute("CREATE TABLE IF NOT EXISTS userReplyThreads (userid INT PRIMARY KEY, threadid INT);")
    sqlconn.execute("CREATE UNIQUE INDEX IF NOT EXISTS threadidIndex on userReplyThreads (threadid);")
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
    query = ("SELECT dbid, id, log, date, message, staff, post FROM badeggs WHERE id=?", [user_id])
    search_results = _db_read(query)

    entries = []
    for result in search_results:
        # SQL stores Python datetimes as strings so we need to format them back
        # Making matters worse, older logs might not have the TZ data at the end, so we need to handle both
        try:
            dt = datetime.strptime(result[3], "%Y-%m-%d %H:%M:%S.%f%z")
        except ValueError:
            dt = datetime.strptime(result[3], "%Y-%m-%d %H:%M:%S.%f")
        entry = UserLogEntry(result[0], result[1], result[2], dt, result[4], result[5], result[6])
        entries.append(entry)

    return entries


def get_user_reply_thread_id(user_id: int) -> int | None:
    """
    Retrieves the user reply thread id associated with a user id from the db.

    :param user_id: The user id to query.
    :return: The thread id, or None if not present.
    """
    query = ("SELECT threadid from userReplyThreads WHERE userid=?", [user_id])
    search_results = _db_read(query)

    if len(search_results) == 0:
        return None

    return search_results[0][0]


def get_user_reply_thread_user_id(thread_id: int) -> int | None:
    """
    Retrieves the user id associated with a user reply thread id from the db.

    :param thread_id: The thread id to query.
    :return: The user id, or None if not present.
    """
    query = ("SELECT userid from userReplyThreads WHERE threadid=?", [thread_id])
    search_results = _db_read(query)

    if len(search_results) == 0:
        return None

    return search_results[0][0]


def set_user_reply_thread(user_id: int, thread_id: int):
    """
    Stores the user reply thread id associated with a user id.

    :param user_id: The user id.
    :param thread_id: The thread id.
    """
    query = ("REPLACE into userReplyThreads (userid, threadid) VALUES (?, ?)", [user_id, thread_id])
    _db_write(query)


def get_warn_count(userid: int) -> int:
    query = ("SELECT COUNT(*) FROM badeggs WHERE id=? AND log = 1", [userid])
    search_results = _db_read(query)

    return search_results[0][0] + 1

def get_note_count(userid: int) -> int:
    query = ("SELECT COUNT(*) FROM badeggs WHERE id=? AND log = 2", [userid])
    search_results = _db_read(query)

    return search_results[0][0] + 1

def add_log(log_entry: UserLogEntry):
    if log_entry.dbid is None:
        query = ("INSERT INTO badeggs (id, log, date, message, staff, post) VALUES (?, ?, ?, ?, ?, ?)", log_entry.as_list())
    else:
        query = ("INSERT OR REPLACE INTO badeggs (dbid, id, log, date, message, staff, post) VALUES (?, ?, ?, ?, ?, ?, ?)", log_entry.as_list())
    _db_write(query)

def remove_log(dbid: int):
    query = ("DELETE FROM badeggs WHERE dbid=?", [dbid])
    _db_write(query)

def clear_user_logs(userid: int):
    logs = search(userid)
    for log in logs:
        if log.dbid is not None:
            remove_log(log.dbid)

def get_watch_list() -> list[int]:
    query = ("SELECT * FROM watching",)
    result = _db_read(query)
    return [x[0] for x in result]

def add_watch(userid: int):
    query = ("INSERT OR REPLACE INTO watching (id) VALUES (?)", [userid])
    _db_write(query)

def del_watch(userid: int):
    query = ("DELETE FROM watching WHERE id=?", [userid])
    _db_write(query)

def get_staffdata(staff: str) -> list[tuple]:
    if not staff:
        query = ("SELECT * FROM staffLogs",)
    else:
        query = ("SELECT * FROM staffLogs WHERE staff=?", [staff])
    return _db_read(query)

def add_staffdata(staff: str, bans: int, warns: int, is_replace: bool):
    if is_replace:
        query = ("REPLACE INTO staffLogs (staff, bans, warns) VALUES (?, ?, ?)", [staff, bans, warns])
    else:
        query = ("INSERT INTO staffLogs (staff, bans, warns) VALUES (?, ?, ?)", [staff, bans, warns])

    _db_write(query)

def get_monthdata(month: str) -> list[tuple]:
    if not month:
        query = ("SELECT * FROM monthLogs",)
    else:
        query = ("SELECT * FROM monthLogs WHERE month=?", [month])
    return _db_read(query)

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
