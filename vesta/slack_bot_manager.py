import io
import re
import time
import asyncio
import traceback
import concurrent

#from slackclient import SlackClient
import slack
from slack import WebClient, RTMClient

from .__version__ import __version__
from . import env
from .format_str import *

# for some issue on WebClient.chat_postMessage()
import nest_asyncio
nest_asyncio.apply()

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

                    typically, I recommend using `argparse`.
                    see `gpu_status_server.py` for more detail.
        """

        self.settings = settings
        self.bot_token = bot_token
        self.database = database
        # only using for format sting
        self.term_width = term_width
        self.client = WebClient(self.bot_token)

        #U8XLD9G5S

        self.cmd_prefix = re.compile(self.settings.KEYWORD_CMD_PREFIX)
        self.re_key_ph = re.compile(self.settings.KEYWORD_PRINT_HOSTS)
        self.re_key_pah = re.compile(self.settings.KEYWORD_PRINT_ALL_HOSTS)
        self.re_key_pahc = re.compile(self.settings.KEYWORD_PRINT_ALL_HOSTS_CMD)
        self.re_key_pahd = re.compile(self.settings.KEYWORD_PRINT_ALL_HOSTS_DETAIL)
        self.re_key_help = re.compile(self.settings.KEYWORD_PRINT_HELP)

        # check keywords are empty or not
        self.valid_key_ph = len(self.settings.KEYWORD_PRINT_HOSTS) > 0
        self.valid_key_pah = len(self.settings.KEYWORD_PRINT_ALL_HOSTS) > 0
        self.valid_key_pahc = len(self.settings.KEYWORD_PRINT_ALL_HOSTS_CMD) > 0
        self.valid_key_pahd = len(self.settings.KEYWORD_PRINT_ALL_HOSTS_DETAIL) > 0
        self.valid_key_help = len(self.settings.KEYWORD_PRINT_HELP) > 0

    def create_response(self, req_content_dict):
        """
            create respose content correspond to the slack keyword
        
            args:
                req_content_dict: dict
                    req_content_dict should be a dict which is made in SlackBot::parse_rtm_data()

            return: dict
                it will returns a dict {"type":type, "content":msg}.
                    type: "message" or "snippet"
                    msg: str, content of posting to slack 

        """

        try:
            request_content = req_content_dict["request"]
            req_channel = req_content_dict["channel"]

            msg = ""

            # print all hosts status
            if self.re_key_pah.search(request_content) is not None and self.valid_key_pah:
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
                    msg += "\n"
                
                return {"type":"snippet", "content":msg}

            # print one host
            elif self.database.has_host(request_content):
                host_states = self.database.host_list[self.database.name_to_hash_table[request_content]]

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

                return {"type":"snippet", "content":msg}

            # print all hosts status in command line printing style
            elif self.re_key_pahc.search(request_content) is not None and self.valid_key_pahc:
                fetch_data = self.database.fetch_all(fetch_num=1)

                msg += "vesta ver. {}\n".format(__version__)+format_gpu_info(fetch_data)
                
                return {"type":"snippet", "content":msg}

            # print all hosts status in detail
            elif self.re_key_pahd.search(request_content) is not None and self.valid_key_pahd:
                fetch_data = self.database.fetch_all(fetch_num=1)

                msg += "vesta ver. {}\n".format(__version__)+format_gpu_detail_info(fetch_data, term_width=self.term_width)
                
                return {"type":"snippet", "content":msg}

            # print all watching hosts
            elif self.re_key_ph.search(request_content) is not None and self.valid_key_ph:
                for host_hash in self.database.host_order:
                    msg += "{}\n".format(self.database.host_list[host_hash]["name"])

                return {"type":"snippet", "content":msg}

            # print command
            elif self.re_key_help.search(request_content) is not None and self.valid_key_help:
                msg = ""
                msg += ("`{}{}`: show all hosts which is watched by the server.\n".format(self.settings.KEYWORD_CMD_PREFIX, self.settings.KEYWORD_PRINT_HOSTS) if self.valid_key_ph else "")
                msg += ("`{}{}`: show all hosts statuses.\n".format(self.settings.KEYWORD_CMD_PREFIX, self.settings.KEYWORD_PRINT_ALL_HOSTS) if self.valid_key_pah else "")
                msg += ("`{}{}`: show all hosts statuses in style of command line.\n".format(self.settings.KEYWORD_CMD_PREFIX, self.settings.KEYWORD_PRINT_ALL_HOSTS_CMD) if self.valid_key_pahc else "")
                msg += ("`{}{}`: show all hosts statuses in detail.\n".format(self.settings.KEYWORD_CMD_PREFIX, self.settings.KEYWORD_PRINT_ALL_HOSTS_DETAIL) if self.valid_key_pahd else "")
                msg += ("`{}<host_name>`: show host statuses in detail.\n".format(self.settings.KEYWORD_CMD_PREFIX))
                msg += ("`{}{}`: show this message.".format(self.settings.KEYWORD_CMD_PREFIX, self.settings.KEYWORD_PRINT_HELP) if self.valid_key_help else "")

                return {"type":"message", "content":msg}

        except Exception as e:
            print_error(e)

        return {"type":None, "content":""}

    def send_snippet(self, msg, parsed_data, start_thread=True):
        try:
            msg = io.StringIO(msg)
            
            if start_thread:
                response = self.client.files_upload(channels=parsed_data["channel"],
                                                    initial_comment="<@{}>".format(parsed_data["user"]),
                                                    title="response: {}".format(parsed_data["user"], parsed_data["request"]),
                                                    file=msg,
                                                    filename='{}.txt'.format(parsed_data["request"]),
                                                    thread_ts=parsed_data["thread_ts"])
            else:
                response = self.client.files_upload(channels=parsed_data["channel"],
                                                    initial_comment="<@{}> ".format(parsed_data["user"]),
                                                    title="response: {}".format(parsed_data["request"]),
                                                    file=msg,
                                                    filename='{}.txt'.format(parsed_data["request"]))
            
            msg.close()

        except Exception as e:
            print_error(e)

    def send_message(self, msg, parsed_data, start_thread=True):
        try:
            if start_thread:
                self.client.chat_postMessage(channel=parsed_data["channel"],
                                             text="<@{}>\n{}".format(parsed_data["user"], msg),
                                             thread_ts=parsed_data["thread_ts"])
            else:
                self.client.chat_postMessage(channel=parsed_data["channel"],
                                             text="<@{}>\n{}".format(parsed_data["user"], msg))

        except Exception as e:
            print_error(e)

    def parse_rtm_data(self, data_dict):
        """
            only return the response to other users with keyword: self.settings.KEYWORD_CMD_PREFIX + <host_name>

            args:
                data_dict: dict
                    it should be a content of dict["data"] from RTMClient message event. 
        """

        req = {}

        try:
            # skip bots message and thread reply
            if ("bot_id"  in data_dict or
                "files"   in data_dict or
                "subtype" in data_dict or
                "upload"  in data_dict):
                return req # {}

            if "user" in data_dict:
                if "text" in data_dict:
                    if self.cmd_prefix.match(data_dict["text"]):
                        req = {"request"   : self.cmd_prefix.sub("", data_dict["text"]),
                               "user"      : data_dict["user"],
                               "channel"   : data_dict["channel"],
                               # in the thread, thread_ts should the parent
                               "thread_ts" : data_dict['ts'] if "thread_ts" not in data_dict else data_dict["thread_ts"]}

        except Exception as e:
            print_error(e)
            req = {}

        return req

    # main routine
    def start(self, loop):
        """
            args:
                loop: asyncio.get_event_loop()
        """

        # I need self context...
        @RTMClient.run_on(event='message')
        async def rtm_message_receive(**payload):
            """
                payload will be like
                {
                    'rtm_client': <slack.rtm.client.RTMClient object at 0x...>,
                    'web_client': <slack.web.client.WebClient object at 0x...>,
                    'data': {
                        'client_msg_id': '...',
                        'suppress_notification': False,
                        'text': 'test message',
                        'user': 'U...',
                        'team': 'T...',
                        'blocks': [
                            {
                                'type': 'rich_text',
                                'block_id': '...',
                                'elements': [
                                    {
                                        'type': 'rich_text_section',
                                        'elements': [
                                            {
                                                'type': 'text',
                                                'text': 'test message'
                                            }
                                        ]
                                    }
                                ]
                            }
                        ],
                        'user_team': 'T...',
                        'source_team': 'T...',
                        'channel': 'C...',
                        'event_ts': 'xxxx.yyyy',
                        'ts': 'xxxx.yyyy'
                    }
                }
            """

            data_dict = payload['data']

            """
                parsed_data will be like
                {
                    "request"   : "...",
                    "user"      : "...",
                    "channel"   : "...",
                    "thread_ts" : "..."
                }
            """
            parsed_data = self.parse_rtm_data(data_dict)

            if len(parsed_data) > 0:
                response = self.create_response(parsed_data)

                if response["type"] == "snippet":
                    # slack python api error?
                    # it seems replying through a thread with snipped (file) makes strange behavior
                    self.send_snippet(response["content"], parsed_data)

                if response["type"] == "message":
                    self.send_message(response["content"], parsed_data)
            else:
                pass

        asyncio.set_event_loop(loop)
        self.rtm_client = RTMClient(token=self.bot_token, connect_method='rtm.start', loop=loop)
        self.rtm_client.start()
