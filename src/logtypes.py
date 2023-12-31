from enum import IntEnum

class LogTypes(IntEnum):
    BAN = 0
    WARN = 1
    NOTE = 2
    KICK = 3
    UNBAN = 4
    SCAM = 5

class UnknownLogTypeException(Exception):
    pass

def present_tense(lt: LogTypes) -> str:
    match lt:
        case LogTypes.BAN | LogTypes.SCAM:
            return "Ban"
        case LogTypes.NOTE:
            return "Note"
        case LogTypes.KICK:
            return "Kick"
        case LogTypes.UNBAN:
            return "Unban"
        case LogTypes.WARN:
            return "Warning"
        case _:
            raise UnknownLogTypeException

def past_tense(lt: LogTypes) -> str:
    match lt:
        case LogTypes.BAN | LogTypes.SCAM:
            return "Banned"
        case LogTypes.NOTE:
            return "Noted"
        case LogTypes.KICK:
            return "Kicked"
        case LogTypes.UNBAN:
            return "Unbanned"
        case LogTypes.WARN:
            return "Warned"
        case _:
            raise UnknownLogTypeException
