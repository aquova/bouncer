import json
from enum import Enum, unique

DATABASE_PATH = "/private/bouncer.db"
# Discord has a 2000 message character limit
CHAR_LIMIT = 2000
# Add extra message if more than threshold number of warns
WARN_THRESHOLD = 3

@unique
class LogTypes(Enum):
    UNBAN = -3
    KICK = -2
    NOTE = -1
    BAN = 0
    WARN = 1

# Read values from config file
config_path = "/private/config.json"
with open(config_path) as config_file:
    cfg = json.load(config_file)

censor_path = "/private/censor.json"
with open(censor_path) as censor_file:
    censor = json.load(censor_file)

# Set values from config file as constants
DISCORD_KEY = cfg['discord']
OWNER = cfg['owner']
CMD_PREFIX = cfg['command_prefix']

HOME_SERVER = cfg['servers']['home']

MAILBOX = cfg['channels']['mailbox']
VALID_INPUT_CHANS = cfg['channels']['listening']
LOG_CHAN = cfg['channels']['log']
SYS_LOG = cfg['channels']['syslog']
WATCHLIST_CHAN = cfg['channels']['watchlist']
BAN_APPEAL = cfg['channels']['ban_appeal']

VALID_ROLES = cfg['roles']

DM_BAN = cfg['DM']['ban']
DM_WARN = cfg['DM']['warn']
DEBUG_BOT = (cfg['debug'].upper() == "TRUE")

CENSOR_LIST = censor['regex']
CENSOR_WATCH = censor['watch_regex']
CENSOR_CHAN = censor['notify_chan']

USER_PLOT = "/private/user_plot.png"
MONTH_PLOT = "/private/month_plot.png"
