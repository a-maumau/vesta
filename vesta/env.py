DEBUG = False

WS_RECEIVE_TIMEOUT = 1.0

# in sec
SLACK_BOT_SLEEP_TIME = 1

SERVER_AVAILABLE = "running"
SERVER_WAITING_UPLINK = "waiting for re-uplink"
SERVER_DOWN = "down"

STATUS_OK = [SERVER_AVAILABLE]
# in this status it will send a notification to slack
STATUS_BAD = [SERVER_WAITING_UPLINK, SERVER_DOWN]

# at least interval time for saving data (in sec.)
# if you want to save all data, set this to 0
SAVE_INTERVAL = 60

# sort type, "ip" or "name"
SORT_BY = "ip"
