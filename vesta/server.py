import os
import re
import json
import time
import random
import socket
import asyncio
import schedule
import requests
import threading
from datetime import datetime

# need some patch
# https://github.com/miguelgrinberg/Flask-SocketIO/issues/65
from gevent import monkey
monkey.patch_all()

# flask
import ssl
from flask import Flask, render_template, redirect, request, abort
from flask_classful import FlaskView, route
from jinja2 import Template, Environment, FileSystemLoader

# for websockets
from gevent import pywsgi, Timeout
from geventwebsocket.handler import WebSocketHandler

from .__version__ import __version__
from . import env
from .database import Database
from .slack_bot_manager import SlackBot
from .path_util import *
from .format_str import *
from .terminal_color import *

def create_response_403(info_msg="forbidden"):
    return json.dumps({"status":"ERROR", "status_code":403, "info":"{}".format(info_msg)})

def create_response_404(info_msg="not found"):
    return json.dumps({"status":"ERROR", "status_code":404, "info":"{}".format(info_msg)})

def send_message_to_slack(slack_webhook, msg, quiet=False, debug=False):
    if slack_webhook != "":
        try:
            resp = requests.post(slack_webhook, data=json.dumps({"text":msg}))
            if resp.history != [] and resp.history != 200 and not quiet:
                print("could not send message to Slack.")
        except Exception as e:
            if debug:
                print(e)

def create_timestamp(timestamp_format):
    timestamp_format_sc = timestamp_format.lower()

    # ex. 20181123204514 -> 2018/11/23 20:45:14
    if timestamp_format_sc == "ymd":
        return datetime.now().strftime("%Y/%m/%d %H:%M:%S")

    # ex. 20181123204514 -> 11/23/2018 20:45:14
    elif timestamp_format_sc == "mdy":
        return datetime.now().strftime("%m/%d/%Y %H:%M:%S")

    # ex. 20181123204514 -> 23/11/2018 20:45:14
    elif timestamp_format_sc == "dmy":
        return datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    # "MDY"
    return datetime.now().strftime("%m/%d/%Y %H:%M:%S")

"""
    # this part is not looking good... should be merged?

    database = None
    @classmethod
    def init(cls, database):
        cls.database = database
"""

"""
    fetched data will be like            
    {
        "host1":{
            "data":[
                {
                    'gpu_data':{
                        'gpu:0':{
                            'available_memory': '10934',
                            'device_num': '0',
                            'gpu_name': 'GeForce GTX 1080 Ti',
                            'gpu_volatile': '0',
                            'processes': [
                                {
                                    'name': '/usr/bin/X',
                                    'pid': '1963',
                                    'used_memory': '148',
                                    'user': 'root'
                                },
                                {
                                    'name': 'compiz',
                                    'pid': '3437',
                                    'used_memory': '84',
                                    'user': 'user1'
                                }
                            ],
                            'temperature': '36',
                            'timestamp': '2018/11/30 23:29:47.115',
                            'total_memory': '11169',
                            'used_memory': '235',
                            'uuid': 'GPU-...'},
                        'gpu:1':{
                            'available_memory': '11170',
                            'device_num': '1',
                            'gpu_name': 'GeForce GTX 1080 Ti',
                            'gpu_volatile': '0',
                            'processes': [],
                            'temperature': '38',
                            'timestamp': '2018/11/30 23:29:47.117',
                            'total_memory': '11172',
                            'used_memory': '2',
                            'uuid': 'GPU-...'
                        }
                    },
                    "timestamp": 20181130232947
                }
            ],
            "ip_address": 127.0.0.1
        },
        "host2":{...}
    }
"""

class StatesView(FlaskView):
    """
        this class take care of `http://<server_address>/states/`
        it will provide stored gpu status information.

        if you want to access to latest data,
        `access http://<server_address>/` which in MainView.
    """

    database = None
    term_width = 80

    @classmethod
    def init(cls, settings, database, term_width=80):
        cls.settings = settings
        cls.database = database
        cls.term_width = term_width

    # filtering
    def before_request(self, name, **kwargs):
        match = re.search(self.settings.VALID_NETWORK, request.remote_addr)
        if match is None:
            abort(403)

    @route('/')
    def all_status(self):
        request_json = request.get_json()
        if request_json:
            pass

        else:        
            fetch_num = request.args.get('fetch_num', default=1, type=int)
            fetch_data = self.database.fetch_all(fetch_num=fetch_num)

        return json.dumps(fetch_data)

    @route('/<string:host_name>/')
    def host_status(self, host_name):
        if self.database.has_host(host_name):
            if request.args.get('term', default=False, type=bool):
                fetch_data = self.database.fetch(host_name, fetch_num=1)

                return "vesta ver. {}\n".format(__version__)+format_gpu_detail_info(fetch_data, term_width=self.term_width)

            else:
                fetch_num = request.args.get('fetch_num', default=1, type=int)
                fetch_data = self.database.fetch(host_name, fetch_num=fetch_num, ignore_down_state=True)

                return json.dumps(fetch_data)
        else:
            return create_response_404("not found")

class RegisterView(FlaskView):
    """
        this class take care of `http://<server_address>/register/`
        it is used by clients to register themselves.
    """

    database = None

    @classmethod
    def init(cls, settings, database):
        cls.settings = settings
        cls.database = database
        # when token is "", we will pass the validation
        cls.token_auth_disable = len(cls.settings.TOKEN) < 1

    def validate_host_name(self, name):
        # for avoiding error in sqlite3, I think there are more tokens cause error...
        name = name.replace(".", "_").replace(",", "_").replace("-", "_").replace("@", "_")
        name = name.replace("[", "_").replace("]", "_").replace(":", "_").replace(";", "_")

        return name

    @route('/', methods=["GET"])
    def rergister(self):
        name = self.validate_host_name(request.args.get('host_name'))
        register_hash_code = request.args.get('token')

        if register_hash_code == self.settings.TOKEN or self.token_auth_disable:
            hash_code = random.getrandbits(128)
            hash_key = "{:x}".format(hash_code)

            if self.database.has_host(name):
                additional_name_hash = random.getrandbits(32)
                name = "{}_{:x}".format(name, additional_name_hash)

            self.database.add_host(hash_key, name, request.remote_addr)

            if not self.settings.QUIET:
                ts = create_timestamp(self.settings.TIMESTAMP_FORMAT)
                print("[ {} ] {}{}[ register ] : {}[{}] hash:{}{}{}".format(ts,
                                                                       terminal_bg.BLUE, terminal_fg.WHITE, 
                                                                       name, request.remote_addr, hash_key,
                                                                       terminal_fg.END, terminal_bg.END))
            msg = self.settings.REGISTER_UPLINK_MSG.format(name)
            send_message_to_slack(self.settings.SLACK_WEBHOOK, msg, self.settings.QUIET, self.settings.DEBUG)

            return json.dumps({"id":hash_key,
                               "register_name":name,
                               "status":"OK",
                               "status_code":200})
        else:
            return create_response_403()

class UpdateView(FlaskView):
    """
        this class take care of `http://<server_address>/update/<host_name>`
        it is used by clients to update their data
    """

    database = None

    @classmethod
    def init(cls, settings, database):
        cls.settings = settings
        cls.database = database
        # when token is "", we will pass the validation
        cls.token_auth_disable = len(cls.settings.TOKEN) < 1
        cls.client_update = {}

    # filtering
    def before_request_client_get_update(self, name, **kwargs):
        match = re.search(self.settings.VALID_NETWORK, request.remote_addr)
        if match is None:
            abort(403)

    @route('/host/<string:hash_key>', methods=["POST"])
    def add_data(self, hash_key):
        register_hash_code = request.args.get('token')

        if register_hash_code == self.settings.TOKEN or self.token_auth_disable:
            if self.database.has_hash(hash_key):
                _thread = threading.Thread(target=self.__add_to_database,
                                           args=(request.get_json(), hash_key, self.database.host_list[hash_key]["name"]))
                _thread.daemon = True
                _thread.start()

                return json.dumps({"status":"OK", "status_code":200})
            else:
                return create_response_404("not in known list")
        else:
            return create_response_403()

    def __add_to_database(self, data, hash_key, host_name):
        if self.database.host_list[hash_key]["status"] in env.STATUS_BAD:
            msg = self.settings.RE_UPLINK_MSG.format(host_name)
            send_message_to_slack(self.settings.SLACK_WEBHOOK, msg, self.settings.QUIET, self.settings.DEBUG)

            if not self.settings.QUIET:
                ts = create_timestamp(self.settings.TIMESTAMP_FORMAT)
                print("[ {} ] {}{}[    UP    ] : {}{}{}".format(ts,
                                                            terminal_bg.GREEN, terminal_fg.BLACK,
                                                            host_name,
                                                            terminal_bg.END, terminal_fg.END))
        else:
            if self.settings.DEBUG:
                ts = create_timestamp(self.settings.TIMESTAMP_FORMAT)
                print("[ {} ] [  UPDATE  ] : {}".format(ts, host_name))

        self.database.add_data(hash_key, data)
        self.__add_queue(self.database.host_list[hash_key]["name"])

    def __add_queue(self, updated_host):
        for key in self.client_update:
            if updated_host in self.database.get_page_host_names(self.client_update[key]["page"]):
                self.client_update[key]["queue"].add(updated_host)

    def fetch_update(self, queue):
        update_data = {}

        for host_name in queue:
            update_data[host_name] = self.database.fetch(host_name, fetch_num=1, return_only_data=True)

        return update_data

    # database store the data only in specific interval,
    # so latest is stored in cache data
    def fetch_cache_update(self, queue):
        update_data = {}

        for host_name in queue:
            update_data[host_name] = self.database.fetch_cache(host_name, return_only_data=True)

        return update_data

    @route('/client/ws', methods=["get"])
    def client_get_update(self):
        if request.environ.get('wsgi.websocket'):
            ws = request.environ['wsgi.websocket']
            client_ip = request.remote_addr

            self.client_update[client_ip] = {"page": 1, "queue":set()}

            while True:
                # wait 1sec for client,
                # and check if new page number is requested or not
                page_num = None
                with Timeout(self.settings.WS_RECEIVE_TIMEOUT, False):
                    page_num = ws.receive()

                if page_num is None:
                    pass
                # if new page number was requested
                else:
                    page_num = int(page_num)
                    if page_num < 1:
                        page_num = 1

                    if page_num != self.client_update[client_ip]["page"]:
                        self.client_update[client_ip]["page"] = page_num

                        page_host_list = self.database.get_page_host_names(self.client_update[client_ip]["page"])
                        update_data = {"update":self.fetch_update(page_host_list),
                                       "page_name_list":page_host_list,
                                       "total_page_num":self.database.total_page}

                        self.client_update[client_ip]["queue"] = set()
                        ws.send(json.dumps(update_data))

                if ws.closed:
                    if client_ip in self.client_update:
                        del self.client_update[client_ip]

                    break
                else:
                    update_data = {"update":self.fetch_cache_update(self.client_update[client_ip]["queue"]),
                                   "page_name_list":self.database.get_page_host_names(self.client_update[client_ip]["page"]),
                                   "total_page_num":self.database.total_page}

                    if update_data["update"] != {}:
                        self.client_update[client_ip]["queue"] = set()
                        ws.send(json.dumps(update_data))

            # return empty content
            return ('', 204)
        else:
            abort(405)

class MainView(FlaskView):
    """
        this class take care of `http://<server_address>/`
        it will provide a webpage and terminal data access if you use url parameter `term=`
    """

    route_base = "/"

    database = None
    term_width = 80

    @classmethod
    def init(cls, settings, database, term_width=80):
        cls.settings = settings
        cls.database = database
        cls.term_width = term_width

    # filtering
    def before_request(self, name, **kwargs):
        match = re.search(self.settings.VALID_NETWORK, request.remote_addr)
        if match is None:
            abort(403)

    def page_element(self, host_name):
        fd = self.database.fetch(host_name, return_only_data=True)

        if fd is not None:
            element = render_template('host_entry.tpl', host_name=host_name, host_ip=fd["ip_address"], host_status=fd["status"],
                                      timestamp=fd["data"][0]["timestamp"], gpu_info=fd["data"][0]["gpu_data"],
                                      ok_statuses=env.STATUS_OK)

            return json.dumps({"element":element, "found":True})
        else:
            return json.dumps({"element":"", "found":False})

    def page_content(self, page_num):
        total_page = self.database.total_page
        if page_num > total_page:
            page_num = total_page
        elif page_num < 1:
            page_num = 1

        fetch_data = self.database.fetch_page(page_num)

        return render_template('index.html', vesta_version=__version__,
                               title=self.settings.MAIN_PAGE_TITLE, description=self.settings.MAIN_PAGE_DESCRIPTION,
                               page_num=page_num, total_page=total_page, page_data=fetch_data, ok_statuses=env.STATUS_OK,
                               server_address=self.settings.IP, server_port=self.settings.PORT_NUM)

    def table_content(self):
        fetch_data = self.database.fetch_all(fetch_num=1)

        ts = create_timestamp(self.settings.TIMESTAMP_FORMAT)

        return render_template('gpu_table.html', vesta_version=__version__,
                               title=self.settings.TABLE_PAGE_TITLE, description=self.settings.TABLE_PAGE_DESCRIPTION,
                               table_data=fetch_data, timestamp=ts,
                               server_address=self.settings.IP, server_port=self.settings.PORT_NUM)

    @route('/gpu_table', methods=["GET"])
    def get_gpu_table(self):
        """
            send back all machine's gpu info.
        """

        if request.args.get('term', default=False, type=bool):
            fetch_data = self.database.fetch_all(fetch_num=1)

            response  = "+------------------------------------------------------------------------------+\n"
            response += "| vesta ver. {} gpu table |\n".format(truncate_str(__version__, length=55, fill_char=" "))
            response += format_gpu_table(fetch_data)

            return response
        else:
            return self.table_content()

    def index(self):
        """
            :root
        """

        if request.args.get('term', default=False, type=bool):
            # url parameter: page is 0, it means not specified which will fetch all.
            page_num = request.args.get('page', default=0, type=int)

            if page_num < 0:
                return create_response_404("invalid page number.")
            elif page_num == 0:
                fetch_data = self.database.fetch_all_cache()

                if request.args.get('detail', default=False, type=bool):
                    response = "vesta ver. {}\n".format(__version__)+format_gpu_detail_info(fetch_data, term_width=self.term_width)
                else:
                    response  = "+------------------------------------------------------------------------------+\n"
                    response += "| vesta ver. {} gpu info. |\n".format(truncate_str(__version__, length=55, fill_char=" "))
                    response += format_gpu_info(fetch_data)
            else:
                fetch_data = self.database.fetch_page(page_num)

                if request.args.get('detail', default=False, type=bool):
                    response = "vesta ver. {}\n".format(__version__)+format_gpu_detail_info(fetch_data, term_width=self.term_width)
                else:
                    response  = "+------------------------------------------------------------------------------+\n"
                    response += "| vesta ver. {} gpu info. |\n".format(truncate_str(__version__, length=55, fill_char=" "))
                    response += format_gpu_info(fetch_data)

            return response
        else:
            if request.args.get('fetch_element', default=False, type=bool):
                return self.page_element(request.args.get('element', default="", type=str))

            return self.page_content(request.args.get('page', default=0, type=int))

class HTTPServer(object):
    def __init__(self, settings):
        """ 
            args:
                settings
                    settings must have following instance variable
                        IP                                      :str
                        PORT_NUM                                :int
                        TOKEN                                   :str
                        SERVER_NAME                             :str
                        BIND_HOST                               :int

                        DB_NAME                                 :str
                        DB_DIR                                  :str
                        TIMESTAMP_FORMAT                        :str -> choice ['YMD', 'MDY', 'DMY']

                        PAGE_PER_HOST_NUM                       :int
                        MAIN_PAGE_TITLE                         :str
                        MAIN_PAGE_DESCRIPTION                   :str
                        TABLE_PAGE_DESCRIPTION                  :str
                        TABLE_PAGE_TITLE                        :str
                        
                        TERM_WIDTH                              :int
                        
                        SORT_BY                                 :str
                        
                        SERVER_SLEEP_TIME                       :int
                        DOWN_TH                                 :int
                        WS_RECEIVE_TIMEOUT                      :int
                        SLACK_BOT_SLEEP_TIME                    :int
                        SAVE_INTERVAL                           :int
                        
                        SLACK_WEBHOOK                           :str
                        SLACK_BOT_TOKEN                         :str
                        SLACK_BOT_POST_CHANNEL                  :str
                        
                        VALID_NETWORK                           :str
                        
                        SCHEDULE_FUNCTION                       :[str]
                        
                        REGISTER_UPLINK_MSG                     :str
                        RE_UPLINK_MSG                           :str
                        HOST_DOWN_MSG                           :str

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
        """

        self.settings = settings

        # in case it's called from other modules
        self.this_module_path = re.sub("server.py", "", re.sub('\s*File\s"', "", os.path.abspath(__file__)))

        self.database_name = self.settings.DB_NAME
        self.database_dir = self.settings.DB_DIR

        self.name = self.settings.SERVER_NAME
        self.ip_addr = socket.gethostbyname(socket.gethostname())
        self.bind_port = self.settings.PORT_NUM
        self.bind_host = self.settings.BIND_HOST
        self.term_width = self.settings.TERM_WIDTH

        self.main_thread = None
        self.app = Flask(self.name,
                         static_folder=self.this_module_path+"/static",
                         template_folder=self.this_module_path+"/templates")

        # in case it doesn't exist
        mkdir(self.database_dir)
        self.database = Database(self.settings, path_join(self.database_dir, self.database_name))

        MainView.init(self.settings, self.database, self.term_width)
        MainView.register(self.app)

        StatesView.init(self.settings, self.database, self.term_width)
        StatesView.register(self.app)

        RegisterView.init(self.settings, self.database)
        RegisterView.register(self.app)

        UpdateView.init(self.settings, self.database)
        UpdateView.register(self.app)

        """
        if settings.SSL_KEY is not None and settings.SSL_CERT is not None:
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
            ssl_context.load_cert_chain(settings.SSL_CERT, settings.SSL_KEY)

            self.wsgi_server = pywsgi.WSGIServer((self.bind_host, self.bind_port), self.app,
                                                 handler_class=WebSocketHandler, ssl_context=ssl_context)
        """
        self.wsgi_server = pywsgi.WSGIServer((self.bind_host, self.bind_port), self.app, handler_class=WebSocketHandler)



        if self.settings.SLACK_BOT_TOKEN != "":
            self.slack_bot = SlackBot(self.settings, self.settings.SLACK_BOT_TOKEN, self.database,
                                      server_info={"server_message":self.settings.SERVER_INFO_MSG.format(ip=self.ip_addr,
                                                                                                         port=self.bind_port,
                                                                                                         bind_host=self.bind_host),
                                                   "IP address": self.ip_addr,
                                                   "open port": self.bind_port,
                                                   "bind host": self.bind_host})
        else:
            self.slack_bot = None

        if self.settings.QUIET:
            import logging
            log = logging.getLogger("werkzeug")
            log.disabled = True
            self.app.logger.disabled = True

    def send_hosts_statuses(self, msg_title="ALL_HOSTS_STATUSES", file_name="statuses.txt"):
        msg = ""

        for host_name in self.database.host_order:
            host = self.database.host_list[host_name]

            msg += "{} : {}\n".format(truncate_str(host["name"], length=16, fill_char=" "),
                                      "DEAD" if host["status"] in env.STATUS_BAD else "Alive")
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

        if len(msg) > 0:
            if self.slack_bot is not None:
                self.slack_bot.send_snippet(msg=msg, channel=self.settings.SLACK_BOT_POST_CHANNEL, title=msg_title, file_name=file_name)

    def watch_and_sleep(self):
        """
            self.settings.DOWN_TH should be set larger number than a interval
            what you are going to send from the host.
        """

        # send greeting message
        if len(self.settings.SERVER_UP_MSG) > 0:
            msg = self.settings.SERVER_UP_MSG.format(ip=self.ip_addr,
                                                     port=self.bind_port,
                                                     bind_host=self.bind_host)
            send_message_to_slack(self.settings.SLACK_WEBHOOK, msg, self.settings.QUIET, self.settings.DEBUG)

        # run some functions, they should be a schedule function
        if self.settings.SCHEDULE_FUNCTION:
            try:
                for sche in self.settings.SCHEDULE_FUNCTION:
                    exec(sche)
            except Exception as e:
                print(e)

        while True:
            schedule.run_pending()
            time.sleep(self.settings.SERVER_SLEEP_TIME)

            for hash_key, host in self.database.host_list.items():
                time_diff = self.database.get_unix_timestamp() - host["last_touch"]
                if time_diff > self.settings.DOWN_TH and not host["status"] in env.STATUS_BAD:
                    msg = self.settings.HOST_DOWN_MSG.format(host_name=host["name"], lost_th=self.settings.DOWN_TH)
                    send_message_to_slack(self.settings.SLACK_WEBHOOK, msg, self.settings.QUIET, self.settings.DEBUG)

                    self.database.host_list[hash_key]["status"] = env.SERVER_DOWN

                    if not self.settings.QUIET:
                        ts = create_timestamp(self.settings.TIMESTAMP_FORMAT)
                        print("[ {} ] {}{}[   DOWN   ] : {}{}{}".format(ts,
                                                                    terminal_bg.RED, terminal_fg.WHITE, 
                                                                    host["name"],
                                                                    terminal_fg.END, terminal_bg.END))

    def start(self, ssl_context=None):
        self.ws_thread = threading.Thread(target=self.wsgi_server.serve_forever)
        self.ws_thread.daemon = True
        self.ws_thread.start()

        if self.slack_bot is not None:
            # not main threads (new threads) do not have event loop, so we will pass it
            loop = asyncio.get_event_loop()
            self.bot_thread = threading.Thread(target=self.slack_bot.start, args=(loop,), daemon=True)
            self.bot_thread.start()

        self.watch_and_sleep()
