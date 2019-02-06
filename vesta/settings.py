# this ip address is the server address for the client which send the gpu information
IP = "127.0.0.1"

# server's open port
PORT_NUM = 8080

# whatever you want, actually it's doing nothing now
TOKEN = '0000'

# how many information to read in each page
PAGE_PER_HOST_NUM = 8

PAGE_TITLE = "AWSOME GPUs"
PAGE_DESCRIPTION = "awsome description"

# you can notificate at slack
SLACK_WEBHOOK = "https://hooks.slack.com/services/<your web hook>"
# bot token
SLACK_BOT_TOKEN = "your BOT token"
# used in server::send_hosts_statuses()
SLACK_BOT_POST_CHANNEL = "your channel"

# this will filter the networks
# it will be used in re.search, so you can use regular expression
VALID_NETWORK = "127.0.0.1"

# you can use python schedule module to schedule the announcement of somethin
# in this case, it will use the function self.send_hosts_statuses for every day at00:00 
# must be a iteratable object
SCHEDULE_FUNCTION = ['schedule.every().day.at("00:00").do(self.send_hosts_statuses, "SCHEDULED_STATUS_REPORT")']

# notification message ########################################
# if you use {} it will be filled with host name
REGISTER_UPLINK_MSG = "⬆︎⬆︎⬆︎ `Uplink` Detected - New uplink from `{}`. Hello!"

# if you use {} it will be filled with host name
UPDATE_UPLINK_MSG = "⬆︎⬆︎⬆︎ `  Up  ` Detected - Uplink from `{}`. Welcome back!"

# if you use {}, you have to use two {} and it will be filled with host name and at least lost connection interval sec
HOST_DOWN_MSG = "⬇︎⬇︎⬇︎ ` Down ` Detected - Connection from `{}` has been lost more than {} sec. Check network and machine."

# set prefix if you want to discriminate commands and usual word
KEYWORD_CMD_PREFIX = ""

# slack bot keywords for printing all host ####################
# if you set to "" i will be disabled
# show all host names
KEYWORD_PRINT_HOSTS = "HOSTS"
# same result as server::send_hosts_statuses()
KEYWORD_PRINT_ALL_HOSTS = "ALL"
# same result as command line using ?term=true
KEYWORD_PRINT_ALL_HOSTS_CMD = "ALL_cmd"
# same result as command line using ?term=true
KEYWORD_PRINT_ALL_HOSTS_DETAIL = "ALL_detail"

# for help message
KEYWORD_PRINT_HELP = "HELP"
