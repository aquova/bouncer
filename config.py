import json
from enum import Enum, unique

DATABASE_PATH = "private/sdv.db"

@unique
class LogTypes(Enum):
    UNBAN = -3
    KICK = -2
    NOTE = -1
    BAN = 0
    WARN = 1

    def __str__(self, cls):
        if self == cls.UNBAN:
            return "Unbanned"
        elif self == cls.KICK:
            return "Kicked"
        elif self == cls.NOTE:
            return "Note"
        elif self == cls.BAN:
            return "Banned"
        else:
            return "Warning"

# Read values from config file
with open('private/config.json') as config_file:
    cfg = json.load(config_file)

# Set values from config file as constants
DISCORD_KEY = cfg['discord']
OWNER = cfg['owner']

VALID_INPUT_CHANS = cfg['channels']['listening']
LOG_CHAN = cfg['channels']['log']
SYS_LOG = cfg['channels']['syslog']

VALID_ROLES = cfg['roles']

DM_BAN = (cfg['DM']['ban'].upper() == "TRUE")
DM_WARN = (cfg['DM']['warn'].upper() == "TRUE")
DEBUG_BOT = (cfg['debug'].upper() == "TRUE")

GATE_MES = cfg['gatekeeper']['message']
GATE_EMOJI = cfg['gatekeeper']['emoji']
GATE_ROLE = cfg['gatekeeper']['role']
