import io
import re
import time
import traceback

from slackclient import SlackClient

from .__version__ import __version__
from .env import *
from .settings import *
from .format_str import *

cmd_prefix = re.compile(KEYWORD_CMD_PREFIX)

# check keywords are empty or not
valid_key_ph = len(KEYWORD_PRINT_HOSTS) > 0
valid_key_pah = len(KEYWORD_PRINT_ALL_HOSTS) > 0
valid_key_pahc = len(KEYWORD_PRINT_ALL_HOSTS_CMD) > 0
valid_key_pahd = len(KEYWORD_PRINT_ALL_HOSTS_DETAIL) > 0
valid_key_help = len(KEYWORD_PRINT_HELP) > 0

def print_error(e):
    traceback.print_exc()
    print(e)

class SlackBot(object):
    def __init__(self, bot_token, database, term_width=80):
        self.bot_token = bot_token
        self.database = database
        # only using for format sting
        self.term_width = term_width
        self.client = SlackClient(self.bot_token)

    def response(self, req):
        try:
            for req_content_dict in req:
                req_host = req_content_dict["request"]
                req_channel = req_content_dict["channel"]

                if len(req_host) < 1:
                    continue 

                msg = ""

                if req_host in KEYWORD_PRINT_ALL_HOSTS and valid_key_pah:
                    for host_name in self.database.host_order:
                        host = self.database.host_list[host_name]
                        
                        msg += "{} : {}\n".format(truncate_str(host["name"], length=16, fill_char=" "), "DEAD" if host["status"] in STATUS_BAD else "Alive")
                        if host["status"] in STATUS_OK:
                            fetch_data = self.database.fetch(host["name"], fetch_num=1, return_only_data=True)

                            if fetch_data["data"] != []:
                                data = fetch_data["data"][-1]

                                for gpu, status in data["gpu_data"].items():
                                    # pass the server's timestamp and host ip
                                    if gpu in ["timestamp", "ip_address"]:
                                        continue

                                    if status["processes"] != []:
                                        msg += "    [{} ({})] {}\n".format(gpu, status["gpu_name"], status["timestamp"])
                                        msg += format_process_str(status["processes"], add_before="        ")
                    msg = io.StringIO(msg)

                # print one host
                elif self.database.has_host(req_host):
                    host_states = self.database.host_list[self.database.name_to_hash_table[req_host]]

                    fetch_data = self.database.fetch_cache(host_states["name"], return_only_data=True)

                    msg += "{} : {}\n".format(truncate_str(host_states["name"], length=16, fill_char=" "),
                                              "DEAD" if host_states["status"] in STATUS_BAD else "Alive")

                    if fetch_data["data"] != []:
                        data = fetch_data["data"][-1]

                        for gpu, status in data["gpu_data"].items():
                            # pass the server's timestamp and host ip
                            if gpu in ["timestamp", "ip_address"]:
                                continue

                            if status["processes"] != []:
                                msg += "    [{} ({})] {}\n".format(gpu, status["gpu_name"], status["timestamp"])
                                msg += format_process_str(status["processes"], add_before="        ")

                    msg = io.StringIO(msg)

                elif req_host in KEYWORD_PRINT_ALL_HOSTS_CMD and valid_key_pahc:
                    fetch_data = self.database.fetch_all(fetch_num=1)

                    msg += "vesta ver. {}\n".format(__version__)+format_gpu_info(fetch_data)
                    msg = io.StringIO(msg)

                elif req_host in KEYWORD_PRINT_ALL_HOSTS_DETAIL and valid_key_pahd:
                    fetch_data = self.database.fetch_all(fetch_num=1)

                    msg += "vesta ver. {}\n".format(__version__)+format_gpu_detail_info(fetch_data, term_width=self.term_width)
                    msg = io.StringIO(msg)

                elif req_host in KEYWORD_PRINT_HOSTS and valid_key_ph:
                    for host_hash in self.database.host_order:
                        msg += "{}\n".format(self.database.host_list[host_hash]["name"])

                    msg = io.StringIO(msg)

                elif req_host in KEYWORD_PRINT_HELP and valid_key_help:
                    msg = ""
                    msg += "`{}{}`: show all host which is watched by server.\n".format(KEYWORD_CMD_PREFIX, KEYWORD_PRINT_HOSTS)
                    msg += "`{}{}`: show all host statuses.\n".format(KEYWORD_CMD_PREFIX, KEYWORD_PRINT_ALL_HOSTS)
                    msg += "`{}{}`: show all host statuses in style of command line.\n".format(KEYWORD_CMD_PREFIX, KEYWORD_PRINT_ALL_HOSTS_CMD)
                    msg += "`{}{}`: show all host statuses in detail.\n".format(KEYWORD_CMD_PREFIX, KEYWORD_PRINT_ALL_HOSTS_DETAIL)
                    msg += "`{}<host_name>`: show host status in detail.\n".format(KEYWORD_CMD_PREFIX)
                    msg += "`{}{}`: show this message.".format(KEYWORD_CMD_PREFIX, KEYWORD_PRINT_HELP)
                    self.client.rtm_send_message(req_channel, msg)

                if isinstance(msg, io.StringIO):
                    self.client.api_call("files.upload", channels=req_channel, file=msg, filename='{}.txt'.format(req_host), title="response: {}".format(req_host))
                    msg.close()

        except Exception as e:
            print_error(e)

    def parse_rtm_data(self, data_array):
        """
            only return the response to other users with keyword: host_name
        """
        req = []

        try:
            for data_dict in data_array:
                # skip bots message
                # expecting bots' message always have this attribute.
                if "bot_id" in data_dict:
                    continue

                if "type" in data_dict:
                    if data_dict["type"] == "message":
                        if "text" in data_dict:
                            if cmd_prefix.match(data_dict["text"]):
                                req.append({"request":cmd_prefix.sub("", data_dict["text"]), "channel":data_dict["channel"]})

        except Exception as e:
            print_error(e)

        return req

    def start(self):
        if self.client.rtm_connect():
            while True:
                while self.client.server.connected is True:
                    req = self.parse_rtm_data(self.client.rtm_read())
                    self.response(req)
                    time.sleep(SLACK_BOT_SLEEP_TIME)

                time.sleep(1)
                if not self.client.rtm_connect():
                    raise Exception("Connection Failed")

        else:
            print("Connection Failed")
