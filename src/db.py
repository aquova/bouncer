# pyright: reportCallInDefaultInitializer=false, reportExplicitAny=false

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

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

    def as_list(self):
        if self.dbid is not None:
            return [self.dbid, self.user_id, self.log_type, self.timestamp, self.log_message, self.staff, self.message_id]
        else:
            return [self.user_id, self.log_type, self.timestamp, self.log_message, self.staff, self.message_id]

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

def _db_read(query: str, params: list[Any] = []) -> list[tuple[Any, ...]]:
    sqlconn = sqlite3.connect(DATABASE_PATH)
    # The * operator in Python expands a tuple into function params
    results = sqlconn.execute(query, params).fetchall()
    sqlconn.close()

    return results

def _db_write(query: str, params: list[Any] = []):
    sqlconn = sqlite3.connect(DATABASE_PATH)
    sqlconn.execute(query, params)
    sqlconn.commit()
    sqlconn.close()

def search(uid: int) -> list[UserLogEntry]:
    query = "SELECT * FROM badeggs WHERE id=?"
    search_results: list[tuple[int, int, LogTypes, str, str, str, int]] = _db_read(query, [uid])

    entries: list[UserLogEntry] = []
    for result in search_results:
        # SQL stores Python datetimes as strings so we need to format them back
        # Making matters worse, there are *three* formats saved in the logs.
        # - An older format without a timezone
        # - The more common newer one with a timezone
        # - A very rarely, some logs don't have any milliseconds stored, possibly due to falling exactly on the second mark
        try:
            dt = datetime.strptime(result[3], "%Y-%m-%d %H:%M:%S.%f%z")
        except ValueError:
            try:
                dt = datetime.strptime(result[3], "%Y-%m-%d %H:%M:%S.%f")
                dt = dt.replace(tzinfo=timezone.utc)
            except ValueError:
                dt = datetime.strptime(result[3], "%Y-%m-%d %H:%M:%S%z")
        entry = UserLogEntry(result[0], result[1], result[2], dt, result[4], result[5], result[6])
        entries.append(entry)

    return entries


def get_user_reply_thread_id(uid: int) -> int | None:
    """
    Retrieves the user reply thread id associated with a user id from the db.

    :param user_id: The user id to query.
    :return: The thread id, or None if not present.
    """
    query = "SELECT threadid from userReplyThreads WHERE userid=?"
    search_results: list[tuple[int]] = _db_read(query, [uid])

    if len(search_results) == 0:
        return None

    return search_results[0][0]


def get_user_reply_thread_user_id(thread_id: int) -> int | None:
    """
    Retrieves the user id associated with a user reply thread id from the db.

    :param thread_id: The thread id to query.
    :return: The user id, or None if not present.
    """
    query = "SELECT userid from userReplyThreads WHERE threadid=?"
    search_results: list[tuple[int]] = _db_read(query, [thread_id])

    if len(search_results) == 0:
        return None

    return search_results[0][0]


def set_user_reply_thread(uid: int, thread_id: int):
    """
    Stores the user reply thread id associated with a user id.

    :param user_id: The user id.
    :param thread_id: The thread id.
    """
    query = "REPLACE into userReplyThreads (userid, threadid) VALUES (?, ?)"
    _db_write(query, [uid, thread_id])


def get_warn_count(uid: int) -> int:
    query = "SELECT COUNT(*) FROM badeggs WHERE id=? AND log = 1"
    search_results: list[tuple[int]] = _db_read(query, [uid])

    return search_results[0][0] + 1

def get_note_count(uid: int) -> int:
    query = "SELECT COUNT(*) FROM badeggs WHERE id=? AND log = 2"
    search_results: list[tuple[int]] = _db_read(query, [uid])

    return search_results[0][0] + 1

def add_log(log_entry: UserLogEntry):
    if log_entry.dbid is None:
        query = "INSERT INTO badeggs (id, log, date, message, staff, post) VALUES (?, ?, ?, ?, ?, ?)"
    else:
        query = "INSERT OR REPLACE INTO badeggs (dbid, id, log, date, message, staff, post) VALUES (?, ?, ?, ?, ?, ?, ?)"
    _db_write(query, log_entry.as_list())

def remove_log(dbid: int):
    query = "DELETE FROM badeggs WHERE dbid=?"
    _db_write(query, [dbid])

def clear_user_logs(uid: int):
    logs = search(uid)
    for log in logs:
        if log.dbid is not None:
            remove_log(log.dbid)

def get_watch_list() -> list[int]:
    query = "SELECT * FROM watching"
    result = _db_read(query)
    return [x[0] for x in result]

def add_watch(uid: int):
    query = "INSERT OR REPLACE INTO watching (id) VALUES (?)"
    _db_write(query, [uid])

def del_watch(uid: int):
    query = "DELETE FROM watching WHERE id=?"
    _db_write(query, [uid])

def get_staffdata(staff: str | None) -> list[tuple[str, int, int]]:
    if staff is None:
        query = "SELECT * FROM staffLogs"
        params = []
    else:
        query = "SELECT * FROM staffLogs WHERE staff=?"
        params = [staff]
    return _db_read(query, params)

def add_staffdata(staff: str, bans: int, warns: int, is_replace: bool):
    if is_replace:
        query = "REPLACE INTO staffLogs (staff, bans, warns) VALUES (?, ?, ?)"
    else:
        query = "INSERT INTO staffLogs (staff, bans, warns) VALUES (?, ?, ?)"

    _db_write(query, [staff, bans, warns])

def get_monthdata(month: str | None) -> list[tuple[str, int, int]]:
    if month is None:
        query = "SELECT * FROM monthLogs"
        params = []
    else:
        query = "SELECT * FROM monthLogs WHERE month=?"
        params = [month]
    return _db_read(query, params)

def add_monthdata(month: str, bans: int, warns: int, is_replace: bool):
    if is_replace:
        query = "REPLACE INTO monthLogs (month, bans, warns) VALUES (?, ?, ?)"
    else:
        query = "INSERT INTO monthLogs (month, bans, warns) VALUES (?, ?, ?)"

    _db_write(query, [month, bans, warns])

def get_weekly_logs() -> list[str]:
    last_week = datetime.now(timezone.utc) - timedelta(weeks=1)
    query = "SELECT staff FROM badeggs WHERE date > ?"
    results = _db_read(query, [format_time(last_week)])
    return [x[0] for x in results]

def get_blocklist() -> list[tuple[str]]:
    query = "SELECT * FROM blocks"
    return _db_read(query)

def add_block(uid: int):
    query = "INSERT INTO blocks (id) VALUES (?)"
    _db_write(query, [uid])

def remove_block(uid: int):
    query = "DELETE FROM blocks WHERE ID=?"
    _db_write(query, [uid])
