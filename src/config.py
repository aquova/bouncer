# pyright: reportAny=false

import yaml

DATABASE_PATH = "./private/bouncer.db"

# Read values from config file
CONFIG_PATH = "./private/config.yaml"
with open(CONFIG_PATH, 'r') as config_file:
    cfg = yaml.safe_load(config_file)

# Set values from config file as constants
DISCORD_KEY: str = cfg['discord']
SERVER_NAME: str = cfg['server_name']

HOME_SERVER: int = cfg['servers']['home']
ADMIN_CATEGORIES: list[int] = cfg['categories']['admin']
BAN_APPEAL_URL: str = cfg['appeal_url']

MAILBOX: int = cfg['channels']['mailbox']
LOG_CHAN: int = cfg['channels']['log']
SYS_LOG: int = cfg['channels']['syslog']
WATCHLIST_CHAN: int = cfg['channels']['watchlist']
SPAM_CHAN: int = cfg['channels']['spam']
IGNORE_SPAM: list[int] = cfg['channels']['ignore_spam']
INFO_CHANS: list[int] = cfg['channels']['info']

VALID_ROLES: list[int] = cfg['roles']['admin']

DM_BAN: bool = cfg['DM']['ban']
DM_WARN: bool = cfg['DM']['warn']

USER_PLOT = "./private/user_plot.png"
MONTH_PLOT = "./private/month_plot.png"

# The ids of roles to invite to new forwarded threads.
# Each role must have less than 100 members for the addition to work
THREAD_ROLES: list[int] = cfg['messageForwarding']['rolesToAddToThreads']
