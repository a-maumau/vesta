DEBUG = False

# this ip address is the server address for the client which send the gpu information
IP = "127.0.0.1"

# server's open port
PORT_NUM = 8080

# whatever you want
TOKEN = '0000'

# you can notificate at slack
SLACK_WEBHOOK = "https://hooks.slack.com/services/<your web hook>"

SERVER_AVAILABLE = "running"
SERVER_WAITING_UPLINK = "waiting"
SERVER_DOWN = "down"

STATUS_OK = [SERVER_AVAILABLE]
# in this status it will send a notification to slack
STATUS_BAD = [SERVER_WAITING_UPLINK, SERVER_DOWN]

# this will filter the networks
# it will be used in re.search, so you can use regular expression
VALID_NETWORK = "192.168.0.[0-9]+"
VALID_NETWORK = "127.0.0.1"

# gpu queries.
# see the help by `nvidia-smi --help-query-gpu` in detail.
GPU_QUERY = [#  (query, alias)
              ('index', "device_num"),       # this must come first
               ('uuid', "uuid"),             #
               ('name', "gpu_name"),         #
    ('temperature.gpu', "temperature"),      # in celsius
       ('memory.total', "total_memory"),     # in MiB
        ('memory.free', "available_memory"), # in MiB
        ('memory.used', "used_memory"),      # in MiB
          ('timestamp', "timestamp"),        #
    ('utilization.gpu', "gpu_volatile")      # in percentage
]

# you can use python schedule module to schedule the announcement of somethin.
# in this case, it will use the function self.send_servere_status for every day at00:00 
SCHEDULE_FUNCTION = 'schedule.every().day.at("00:00").do(self.send_server_status)'

# if you use {} it will be filled with host name
REGISTER_UPLINK_MSG = "⬆︎⬆︎⬆︎ `Uplink` Detected - New uplink from `{}`. Hello!"

# if you use {} it will be filled with host name
UPDATE_UPLINK_MSG = "⬆︎⬆︎⬆︎ `  Up  ` Detected - Uplink from `{}`. Welcome back!"

# if you use {}, you have to use two {} and it will be filled with host name and at least lost connection interval sec
HOST_DOWN_MSG = "⬇︎⬇︎⬇︎ ` Down ` Detected - Connection from `{}` has been lost more than {} sec. Check network and machine."
