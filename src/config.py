import json
from enum import Enum, unique

DATABASE_PATH = "./private/bouncer.db"
USERID_LOG_PATH = "./private/uid.txt"
# Discord has a 2000 message character limit
CHAR_LIMIT = 2000
# Add extra message if more than threshold number of warns
WARN_THRESHOLD = 3

@unique
class LogTypes(Enum):
    SCAM = -4
    UNBAN = -3
    KICK = -2
    NOTE = -1
    BAN = 0
    WARN = 1

# Read values from config file
CONFIG_PATH = "./private/config.json"
with open(CONFIG_PATH) as config_file:
    cfg = json.load(config_file)

# Set values from config file as constants
DISCORD_KEY = cfg['discord']
OWNER = cfg['owner']
CMD_PREFIX = cfg['command_prefix']

HOME_SERVER = cfg['servers']['home']

INPUT_CATEGORIES = cfg['categories']['listening']
MAILBOX = cfg['channels']['mailbox']
LOG_CHAN = cfg['channels']['log']
SYS_LOG = cfg['channels']['syslog']
WATCHLIST_CHAN = cfg['channels']['watchlist']
SPAM_CHAN = cfg['channels']['spam']
IGNORE_SPAM = cfg['channels']['ignore_spam']

VALID_ROLES = cfg['roles']['admin']

DM_BAN = cfg['DM']['ban']
DM_WARN = cfg['DM']['warn']
DEBUG_BOT = (cfg['debug'].upper() == "TRUE")

USER_PLOT = "./private/user_plot.png"
MONTH_PLOT = "./private/month_plot.png"

# list of int: the ids of roles to invite to new forwarded threads
#              each role must have less than 100 members for the addition to work
THREAD_ROLES = cfg['messageForwarding']['rolesToAddToThreads']
