import json

DATABASE_PATH = "./private/bouncer.db"
# Add extra message if more than threshold number of warns
WARN_THRESHOLD = 3

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

USER_PLOT = "./private/user_plot.png"
MONTH_PLOT = "./private/month_plot.png"

# list of int: the ids of roles to invite to new forwarded threads
#              each role must have less than 100 members for the addition to work
THREAD_ROLES = cfg['messageForwarding']['rolesToAddToThreads']
