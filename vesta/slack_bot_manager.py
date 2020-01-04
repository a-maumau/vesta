import io
import re
import ssl 
import time
import certifi
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
"""
    comment outed
    it seems to raise
        RuntimeError: Event loop stopped before Future completed
    I cannot solve it

    # to-fix
"""
import nest_asyncio
nest_asyncio.apply()

def print_error(e, additional=""):
    if len(additional) > 0:
        print(additional)

    traceback.print_exc()
    print(e)

"""
    currentlly this class has a issue of rasing
        "RuntimeError: This event loop is already running".
    I couldn't fix it, but it will work anyway.
    so I will keep this way when the day this could be solved.
"""
class SlackBot(object):
    # this is max.
    # if you want to you more than this, we need to handle the pagination
    slack_api_fetch_limit = 1000

    def __init__(self, settings, bot_token, database, term_width=80, server_info={"server_message":""}):
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
                        DEBUG                                   :bool

                    typically, I recommend using `argparse`.
                    see `gpu_status_server.py` for more detail.
                
                bot_token: str
                database: vesta::Database
                term_width: int
                server_info: dict

        """

        self.settings = settings
        self.bot_token = bot_token
        self.database = database
        # only using for format sting
        self.term_width = term_width
        self.server_info = server_info

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self.ssl_context = ssl.create_default_context(cafile=certifi.where())
        self.client = WebClient(self.bot_token, ssl=self.ssl_context, loop=loop)

        self.cmd_prefix = re.compile(self.settings.KEYWORD_CMD_PREFIX)
        self.re_key_ph = re.compile(self.settings.KEYWORD_PRINT_HOSTS)
        self.re_key_pah = re.compile(self.settings.KEYWORD_PRINT_ALL_HOSTS)
        self.re_key_pahc = re.compile(self.settings.KEYWORD_PRINT_ALL_HOSTS_CMD)
        self.re_key_pahd = re.compile(self.settings.KEYWORD_PRINT_ALL_HOSTS_DETAIL)
        self.re_key_print_host_info = re.compile(self.settings.KEYWORD_PRINT_HOST_INFO)
        self.re_key_help = re.compile(self.settings.KEYWORD_PRINT_HELP)

        # check keywords are empty or not
        self.valid_key_ph = len(self.settings.KEYWORD_PRINT_HOSTS) > 0
        self.valid_key_pah = len(self.settings.KEYWORD_PRINT_ALL_HOSTS) > 0
        self.valid_key_pahc = len(self.settings.KEYWORD_PRINT_ALL_HOSTS_CMD) > 0
        self.valid_key_pahd = len(self.settings.KEYWORD_PRINT_ALL_HOSTS_DETAIL) > 0
        self.valid_key_server_info = len(self.settings.KEYWORD_PRINT_HOST_INFO) > 0
        self.valid_key_help = len(self.settings.KEYWORD_PRINT_HELP) > 0

        self.__create_user_list()
        self.__create_dm_channel_list()

    def __create_user_list(self):
        """
            this function will 

            users_data will be like
            {
                'ok': True,
                'members': [
                    {
                        'id': 'USLACKBOT',
                        'team_id': 'T...',
                        'name': 'slackbot',
                        'deleted': False,
                        'color': '757575',
                        'real_name': 'Slackbot',
                        'tz': None,
                        'tz_label': 'Pacific Standard Time',
                        'tz_offset': -28800,
                        'profile': {
                            'title': '',
                            'phone': '',
                            'skype': '',
                            'real_name': 'Slackbot',
                            'real_name_normalized': 'Slackbot',
                            'display_name': 'Slackbot',
                            'display_name_normalized': 'Slackbot',
                            'fields': None,
                            'status_text': '',
                            'status_emoji': '',
                            'status_expiration': 0,
                            'avatar_hash': 'sv41d8cd98f0',
                            'always_active': True,
                            'first_name': 'slackbot',
                            'last_name': '',
                            'image_24': 'https://a.slack-edge.com/80588/img/slackbot_24.png',
                            ...
                            'image_512': 'https://a.slack-edge.com/80588/img/slackbot_512.png',
                            'status_text_canonical': '',
                            'team': 'T...'
                        },
                        'is_admin': False,
                        'is_owner': False,
                        'is_primary_owner': False,
                        'is_restricted': False,
                        'is_ultra_restricted': False,
                        'is_bot': False,
                        'is_app_user': False,
                        'updated': 0
                    },
                    {...}
                ],
                'cache_ts': 157...,
                'warning': 'superfluous_charset',
                'response_metadata': {
                    'next_cursor': '',
                    'warnings': ['superfluous_charset']
                }
            }
        """

        users_data = self.client.users_list(limit=self.slack_api_fetch_limit)
        members_data = users_data["members"]

        self.cache_ts = users_data["cache_ts"]

        # dict for id
        self.email_to_user_id = {}
        self.user_name_to_user_id = {}

        for member_data_dict in members_data:
            if member_data_dict["is_bot"] or member_data_dict["id"] == "USLACKBOT":
                continue

            self.email_to_user_id[member_data_dict["profile"]["email"]] = member_data_dict["id"]
            self.user_name_to_user_id[member_data_dict["profile"]["display_name"]] = member_data_dict["id"]

    def __update_user_list(self):
        self.__create_user_list()

    def __create_dm_channel_list(self):
        self.user_id_to_dm_channel = {}

        """
            dm_channel_data will be like
            {
                'ok': True,
                'channels': [
                    {
                        'id': 'D...',
                        'created': 1...,
                        'is_archived': False,
                        'is_im': True,
                        'is_org_shared': False,
                        'user': 'U...',
                        'is_user_deleted': False,
                        'priority': 0
                    }, 
                    {...}
                ],
                'response_metadata': {'next_cursor': ''}
            }
        """
        dm_channel_data = self.client.conversations_list(limit=self.slack_api_fetch_limit, types="im")
        for user_data in dm_channel_data['channels']:
            self.user_id_to_dm_channel[user_data["user"]] = user_data["id"]

        #print(self.user_id_to_dm_channel)

    def __update_dm_channel_list(self):
        self.__create_dm_channel_list()

    def __create_cmd_message(self):
        msg = ""
        msg += "`{}{}`: show all hosts which is watched by the server.\n".format(self.settings.KEYWORD_CMD_PREFIX, self.settings.KEYWORD_PRINT_HOSTS) if self.valid_key_ph else ""
        msg += "`{}{}`: show all hosts statuses.\n".format(self.settings.KEYWORD_CMD_PREFIX, self.settings.KEYWORD_PRINT_ALL_HOSTS) if self.valid_key_pah else ""
        msg += "`{}{}`: show all hosts statuses in style of command line.\n".format(self.settings.KEYWORD_CMD_PREFIX, self.settings.KEYWORD_PRINT_ALL_HOSTS_CMD) if self.valid_key_pahc else ""
        msg += "`{}{}`: show all hosts statuses in detail.\n".format(self.settings.KEYWORD_CMD_PREFIX, self.settings.KEYWORD_PRINT_ALL_HOSTS_DETAIL) if self.valid_key_pahd else ""
        msg += "`{}<host_name>`: show host statuses in detail.\n".format(self.settings.KEYWORD_CMD_PREFIX)
        msg += "`{}{}`: show server information.\n".format(self.settings.KEYWORD_CMD_PREFIX, self.settings.KEYWORD_PRINT_HOST_INFO) if self.valid_key_help else ""
        msg += "`{}{} <host_name>`: show information of <host_name>.\n".format(self.settings.KEYWORD_CMD_PREFIX, self.settings.KEYWORD_PRINT_HOST_INFO) if self.valid_key_help else ""
        msg += "`{}{}`: show this message.".format(self.settings.KEYWORD_CMD_PREFIX, self.settings.KEYWORD_PRINT_HELP) if self.valid_key_help else ""

        return msg

    def create_cmd_response(self, req_content_dict):
        """
            create respose content correspond to the slack keyword
        
            args:
                req_content_dict: dict
                    req_content_dict should be a dict which is made in SlackBot::parse_rtm_data_for_cmd()

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

            # print server and host info
            elif self.re_key_print_host_info.search(request_content) is not None and self.valid_key_server_info:
                host_name = self.re_key_print_host_info.sub("", request_content)
                host_name = re.sub("[ ]+", "", host_name)

                print(host_name, len(host_name))

                if len(host_name) < 1:
                    # server info

                    """
                            at now, I think there will be not too long message.
                            so we will send the message in type:message
                    """
                    msg = "```\n"
                    msg += "server message: {}\n\n".format(self.server_info["server_message"])
                    for info_k, info_v in self.server_info.items():
                        if info_k == "server_message":
                            continue

                        msg += "{}: `{}`\n".format(info_k, info_v)
                    msg = "```\n"

                    return {"type":"message", "content":msg}
                else:
                    # host info
                    msg = ""

                    """
                            host_info will be like
                            {
                                'cache_data': None,
                                'ip_address': '127.0.0.1',
                                'last_touch': 0,
                                'last_update': 0,
                                'name': 'mau_local',
                                'status': 'waiting for re-uplink'
                                }
                    """
                    host_info = self.database.fetch_host_info(host_name)
                    if host_info is None:
                        msg += "there is no host name {}".format(host_name)

                        return {"type":"message", "content":msg}

                    else:
                        """
                            at now, I think there will be not too long message.
                            so we will send the message in type:message
                        """
                        msg += "```\n" 
                        msg += "Info:\n"
                        msg += "    Host name   : {}\n".format(host_info["name"])
                        msg += "    IP address  : {}\n".format(host_info["ip_address"])
                        msg += "    Last update : {}\n".format(self.database.format_unix_timestamp(host_info["last_update"]))
                        msg += "    Status      : {}\n".format(host_info["status"])
                        msg += "```"

                        return {"type":"message", "content":msg}

            # print available command
            elif self.re_key_help.search(request_content) is not None and self.valid_key_help:
                msg = self.__create_cmd_message()

                return {"type":"message", "content":msg}

        except Exception as e:
            print_error(e)

        return {"type":None, "content":""}

    def search_user_id(self, user):
        if user in self.user_name_to_user_id:
            return self.user_name_to_user_id[user]

        if user in self.email_to_user_id:
            return self.email_to_user_id[user]

        # it might be old list, so we will update the list
        self.__update_user_list()
        self.__create_dm_channel_list()

        if user in self.user_name_to_user_id:
            return self.user_name_to_user_id[user]

        if user in self.email_to_user_id:
            return self.email_to_user_id[user]

        return None

    def search_user_dm_channel(self, user_id):
        if user_id in self.user_id_to_dm_channel:
            return self.user_id_to_dm_channel[user_id]

        return None

    def send_direct_message(self, msg, user, dm_channel=None):
        if dm_channel is not None:
            self.send_message(msg, user_id, thread_ts="")

        else:
            user_id = self.search_user_id(user)
            if user_id is not None:
                dm_channel = self.search_user_dm_channel(user_id)
                # we have stored the im channel, but we also can search it every time.
                # dm_channel = self.client.conversations_open(users=user_id)['channel']['id']
                
                if dm_channel is not None:
                    self.send_message("<@{}>\n{}".format(user_id, msg), dm_channel, thread_ts="")

    def send_snippet(self, msg, channel, title="", file_name="msg.txt", initial_comment="", thread_ts=""):
        """
            send string message as snippet

            args:
                msg             : str
                channel         : str
                title           : str
                file_name       : str
                initial_comment : str
                thread_ts       : str

                "channel" should be a "#channel_name" or "Cxxxxx" styled
        """

        try:
            msg = io.StringIO(msg)
            
            #if len(thread_ts:
            response = self.client.files_upload(file=msg,
                                                channels=channel,
                                                title=title,
                                                filename=file_name,
                                                initial_comment=initial_comment,
                                                thread_ts=thread_ts)            
            msg.close()

        except Exception as e:
            if self.settings.DEBUG:
                print_error(e, "in send snippet")

    def send_message(self, msg, channel, thread_ts=""):
        try:
            response = self.client.chat_postMessage(text=msg,
                                                    channel=channel,
                                                    thread_ts=thread_ts)

        except Exception as e:
            if self.settings.DEBUG:
                print_error(e, "in send_message")

    def parse_rtm_data_for_cmd(self, data_dict):
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
                        request = self.cmd_prefix.sub("", data_dict["text"])
                        req = {"request"         : request,
                               "user_id"         : data_dict["user"],
                               "channel"         : data_dict["channel"],
                               "title"           : "response: {}".format(request),
                               "file_name"       : "{}.txt".format(request),
                               "initial_comment" : "<@{}>".format(data_dict["user"]),
                               # in the thread, thread_ts should the parent
                               "thread_ts"       : data_dict['ts'] if "thread_ts" not in data_dict else data_dict["thread_ts"]}

        except Exception as e:
            print_error(e)
            req = {}

        return req

    # main routine
    def start_rtm(self, loop):
        """
            args:
                loop: asyncio.get_event_loop()
        """
        @slack.RTMClient.run_on(event="member_joined_channel")
        async def onboarding_message(**payload):
            """
                it seems this will be received only from joined channel.

                payload will be like
                {
                    'rtm_client': <slack.rtm.client.RTMClient>,
                    'web_client': <slack.web.client.WebClient>,
                    'data': {
                        'user': 'U...',
                        'channel': 'C...',
                        'channel_type': 'C', 
                        'team': 'T...',
                        'event_ts': '15...',
                        'ts': '15...'
                    }
                }
            """

            if len(self.settings.SLACKBOT_MEMBER_JOINED_CHANNEL_MSG) > 0:

                user_id = payload["data"]["user"]
                channel = payload["data"]["channel"]
                ts = payload["data"]["ts"]

                # Post the onboarding message.
                #await start_onboarding(web_client, user_id, channel)
                self.send_message(msg=self.settings.SLACKBOT_MEMBER_JOINED_CHANNEL_MSG.format(user="<@{}>".format(user_id), help_msg=self.__create_cmd_message()),
                                  channel=channel,
                                  # DM's channel id will start from "D"
                                  thread_ts="" if re.match("D", channel) else ts)

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
                    "request"         : "...",
                    "user_id"         : "...",
                    "channel"         : "...",
                    "title"           : "...",
                    "file_name"       : "...",
                    "initial_comment" : "...",
                    "thread_ts"       : "..."
                }
            """
            parsed_data = self.parse_rtm_data_for_cmd(data_dict)

            if len(parsed_data) > 0:
                response = self.create_cmd_response(parsed_data)

                if response["type"] == "snippet":
                    self.send_snippet(msg=response["content"],
                                      channel=parsed_data["channel"],
                                      title=parsed_data["title"],
                                      file_name=parsed_data["file_name"],
                                      initial_comment=parsed_data["initial_comment"],
                                      # DM's channel id will start from "D"
                                      thread_ts="" if re.match("D", parsed_data["channel"]) else parsed_data["thread_ts"])

                if response["type"] == "message":
                    self.send_message(msg="<@{}>\n{}".format(parsed_data["user_id"], response["content"]),
                                                  channel=parsed_data["channel"],
                                                  # DM's channel id will start from "D"
                                                  thread_ts="" if re.match("D", parsed_data["channel"]) else parsed_data["thread_ts"])
            else:
                pass

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self.rtm_client = RTMClient(token=self.bot_token, connect_method='rtm.start', ssl=self.ssl_context, run_async=False, loop=loop)
        self.rtm_client.start()
        