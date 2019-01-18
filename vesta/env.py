DEBUG = False

SERVER_AVAILABLE = "running"
SERVER_WAITING_UPLINK = "waiting for re-uplink"
SERVER_DOWN = "down"

STATUS_OK = [SERVER_AVAILABLE]
# in this status it will send a notification to slack
STATUS_BAD = [SERVER_WAITING_UPLINK, SERVER_DOWN]

# at least interval time for saving data (in sec.)
SAVE_INTERVAL = 30
