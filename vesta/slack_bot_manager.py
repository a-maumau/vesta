import io
import re
import time
import traceback

from slackclient import SlackClient

from .__version__ import __version__
from . import env
from .format_str import *

def print_error(e):
    traceback.print_exc()
    print(e)

class SlackBot(object):
    def __init__(self, settings, bot_token, database, term_width=80):
        """
            args:
                settings
                    settings must have following instance variable
                        SLACK_BOT_SLEEP_TIME                    :int
                        SLACK_WEBHOOK                           :str
                        SLACK_BOT_TOKEN                         :str
                        SLACK_BOT_POST_CHANNEL                  :str
                        KEYWORD_CMD_PREFIX                      :str
                        KEYWORD_PRINT_HOSTS                     :str
                        KEYWORD_PRINT_ALL_HOSTS                 :str
                        KEYWORD_PRINT_ALL_HOSTS_CMD             :str
                        KEYWORD_PRINT_ALL_HOSTS_DETAIL          :str
                        KEYWORD_PRINT_HELP                      :str
                        QUIET                                   :bool

                typically, I recommend using `argparse`
                see `gpu_status_server.py`
        """

        self.settings = settings
        self.bot_token = bot_token
        self.database = database
        # only using for format sting
        self.term_width = term_width
        self.client = SlackClient(self.bot_token)

        self.cmd_prefix = re.compile(self.settings.KEYWORD_CMD_PREFIX)

        # check keywords are empty or not
        self.valid_key_ph = len(self.settings.KEYWORD_PRINT_HOSTS) > 0
        self.valid_key_pah = len(self.settings.KEYWORD_PRINT_ALL_HOSTS) > 0
        self.valid_key_pahc = len(self.settings.KEYWORD_PRINT_ALL_HOSTS_CMD) > 0
        self.valid_key_pahd = len(self.settings.KEYWORD_PRINT_ALL_HOSTS_DETAIL) > 0
        self.valid_key_help = len(self.settings.KEYWORD_PRINT_HELP) > 0

    def response(self, req):
        """
            respose to the slack keyword
        
            args:
                req: dict
                    req should be a dict which is made in SlackBot::parse_rtm_data()
        """
        try:
            for req_content_dict in req:
                req_host = req_content_dict["request"]
                req_channel = req_content_dict["channel"]

                if len(req_host) < 1:
                    continue 

                msg = ""

                # print all hosts status
                if req_host in settings.KEYWORD_PRINT_ALL_HOSTS and self.valid_key_pah:
                    for host_name in self.database.host_order:
                        host = self.database.host_list[host_name]
                        
                        msg += "{} : {}\n".format(truncate_str(host["name"], length=16, fill_char=" "), "DEAD" if host["status"] in env.STATUS_BAD else "Alive")
                        if host["status"] in env.STATUS_OK:
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
                    
                    self.send_snippet(msg, req_channel, req_host, req_host)

                # print one host
                elif self.database.has_host(req_host):
                    host_states = self.database.host_list[self.database.name_to_hash_table[req_host]]

                    fetch_data = self.database.fetch_cache(host_states["name"], return_only_data=True)

                    msg += "{} : {}\n".format(truncate_str(host_states["name"], length=16, fill_char=" "),
                                              "DEAD" if host_states["status"] in env.STATUS_BAD else "Alive")

                    if fetch_data["data"] != []:
                        data = fetch_data["data"][-1]

                        for gpu, status in data["gpu_data"].items():
                            # pass the server's timestamp and host ip
                            if gpu in ["timestamp", "ip_address"]:
                                continue

                            if status["processes"] != []:
                                msg += "    [{} ({})] {}\n".format(gpu, status["gpu_name"], status["timestamp"])
                                msg += format_process_str(status["processes"], add_before="        ")

                    self.send_snippet(msg, req_channel, req_host, req_host)

                # print all hosts status in command line printing style
                elif req_host in self.settings.KEYWORD_PRINT_ALL_HOSTS_CMD and self.valid_key_pahc:
                    fetch_data = self.database.fetch_all(fetch_num=1)

                    msg += "vesta ver. {}\n".format(__version__)+format_gpu_info(fetch_data)
                    
                    self.send_snippet(msg, req_channel, req_host, req_host)

                # print all hosts status in detail
                elif req_host in self.settings.KEYWORD_PRINT_ALL_HOSTS_DETAIL and self.valid_key_pahd:
                    fetch_data = self.database.fetch_all(fetch_num=1)

                    msg += "vesta ver. {}\n".format(__version__)+format_gpu_detail_info(fetch_data, term_width=self.term_width)
                    
                    self.send_snippet(msg, req_channel, req_host, req_host)

                # print all watching hosts
                elif req_host in self.settings.KEYWORD_PRINT_HOSTS and self.valid_key_ph:
                    for host_hash in self.database.host_order:
                        msg += "{}\n".format(self.database.host_list[host_hash]["name"])

                    self.send_snippet(msg, req_channel, req_host, req_host)

                # print command
                elif req_host in self.settings.KEYWORD_PRINT_HELP and self.valid_key_help:
                    msg = ""
                    msg += ("`{}{}`: show all hosts which is watched by the server.\n".format(self.settings.KEYWORD_CMD_PREFIX, self.settings.KEYWORD_PRINT_HOSTS) if self.valid_key_ph else "")
                    msg += ("`{}{}`: show all hosts statuses.\n".format(self.settings.KEYWORD_CMD_PREFIX, self.settings.KEYWORD_PRINT_ALL_HOSTS) if self.valid_key_pah else "")
                    msg += ("`{}{}`: show all hosts statuses in style of command line.\n".format(self.settings.KEYWORD_CMD_PREFIX, self.settings.KEYWORD_PRINT_ALL_HOSTS_CMD) if self.valid_key_pahc else "")
                    msg += ("`{}{}`: show all hosts statuses in detail.\n".format(self.settings.KEYWORD_CMD_PREFIX, self.settings.KEYWORD_PRINT_ALL_HOSTS_DETAIL) if self.valid_key_pahd else "")
                    msg += ("`{}<host_name>`: show host statuses in detail.\n".format(self.settings.KEYWORD_CMD_PREFIX))
                    msg += ("`{}{}`: show this message.".format(self.settings.KEYWORD_CMD_PREFIX, self.settings.KEYWORD_PRINT_HELP) if self.valid_key_help else "")

                    self.client.rtm_send_message(req_channel, msg)

        except Exception as e:
            print_error(e)

    def send_snippet(self, msg, req_channel, response_name="response", file_name="response"):
        try:
            msg = io.StringIO(msg)
            
            self.client.api_call("files.upload", channels=req_channel, title="response: {}".format(response_name),
                                 file=msg, filename='{}.txt'.format(file_name))
            
            msg.close()

        except Exception as e:
            print_error(e)

    def parse_rtm_data(self, data_array):
        """
            only return the response to other users with keyword: self.settings.KEYWORD_CMD_PREFIX + <host_name>

            args:
                data_array
                    object from rtm_read()
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
                            if self.cmd_prefix.match(data_dict["text"]):
                                req.append({"request":self.cmd_prefix.sub("", data_dict["text"]), "channel":data_dict["channel"]})

        except Exception as e:
            print_error(e)

        return req

    # main routine
    def start(self):
        if self.client.rtm_connect(auto_reconnect=True):
            while True:
                while self.client.server.connected is True:
                    req = self.parse_rtm_data(self.client.rtm_read())
                    self.response(req)
                    time.sleep(self.settings.SLACK_BOT_SLEEP_TIME)

                time.sleep(10)
                if not self.client.rtm_connect(auto_reconnect=True):
                    raise Exception("Connection Failed")

        else:
            print("Connection Failed")
