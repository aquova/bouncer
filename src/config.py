import yaml

DATABASE_PATH = "./private/bouncer.db"

# Read values from config file
CONFIG_PATH = "./private/config.yaml"
with open(CONFIG_PATH, 'r') as config_file:
    cfg = yaml.safe_load(config_file)

# Set values from config file as constants
DISCORD_KEY = cfg['discord']
SERVER_NAME = cfg['server_name']

HOME_SERVER = cfg['servers']['home']
BAN_APPEAL_URL = cfg['appeal_url']

MAILBOX = cfg['channels']['mailbox']
LOG_CHAN = cfg['channels']['log']
SYS_LOG = cfg['channels']['syslog']
WATCHLIST_CHAN = cfg['channels']['watchlist']
SPAM_CHAN = cfg['channels']['spam']
IGNORE_SPAM = cfg['channels']['ignore_spam']
INFO_CHANS = cfg['channels']['info']

VALID_ROLES = cfg['roles']['admin']

DM_BAN = cfg['DM']['ban']
DM_WARN = cfg['DM']['warn']

USER_PLOT = "./private/user_plot.png"
MONTH_PLOT = "./private/month_plot.png"

# list of int: the ids of roles to invite to new forwarded threads
#              each role must have less than 100 members for the addition to work
THREAD_ROLES = cfg['messageForwarding']['rolesToAddToThreads']
