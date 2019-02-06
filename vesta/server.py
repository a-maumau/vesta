import os
import re
import json
import time
import random
import schedule
import argparse
import requests
import threading
from datetime import datetime

# flask
import ssl
from flask import Flask, render_template, redirect, request, abort
from flask_classful import FlaskView, route
from jinja2 import Template, Environment, FileSystemLoader

# for websockets
from gevent import pywsgi, Timeout
from geventwebsocket.handler import WebSocketHandler

from .__version__ import __version__
from .database import DataBase
from .slack_bot_manager import SlackBot
from .env import *
from .settings import *
from .path_util import *
from .format_str import *
from .terminal_color import *

# need some patch
# https://github.com/miguelgrinberg/Flask-SocketIO/issues/65
from gevent import monkey
monkey.patch_all()

def create_response_403(info_msg="forbidden"):
    return json.dumps({"status":"ERROR", "status_code":403, "info":"{}".format(info_msg)})

def create_response_404(info_msg="not found"):
    return json.dumps({"status":"ERROR", "status_code":404, "info":"{}".format(info_msg)})

def send_uplink_detection(msg, host_name):
    try:
        resp = requests.post(SLACK_WEBHOOK, data=json.dumps({"text":msg.format(host_name)}))
        if resp.history != [] and resp.history != 200:
                print("could not send message to Slack.")
    except Exception as e:
        print(e)

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
    database = None

    @classmethod
    def init(cls, database, term_width=60):
        cls.database = database
        cls.term_width = term_width

    # filtering
    def before_request(self, name, **kwargs):
        match = re.search(VALID_NETWORK, request.remote_addr)
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
    database = None

    @classmethod
    def init(cls, database):
        cls.database = database

    def send_uplink_detection(self, host_name):
        msg = REGISTER_UPLINK_MSG.format(host_name)
        
        resp = requests.post(SLACK_WEBHOOK, data=json.dumps({"text":msg}))
        if resp.history != [] and resp.history != 200:
            print("could not send message to Slack.")

    def validate_host_name(self, name):
        # for avoiding error in sqlite3, I think there is more token cause error...
        name = name.replace(".", "_").replace(",", "_").replace("-", "_").replace("@", "_")
        name = name.replace("[", "_").replace("]", "_").replace(":", "_").replace(";", "_")

        return name

    @route('/', methods=["GET"])
    def rergister(self):
        name = self.validate_host_name(request.args.get('host_name'))
        register_hash_code = request.args.get('token')

        if register_hash_code == TOKEN:
            hash_code = random.getrandbits(128)
            hash_key = "{:x}".format(hash_code)

            if self.database.has_host(name):
                additional_name_hash = random.getrandbits(32)
                name = "{}_{:x}".format(name, additional_name_hash)

            self.database.add_host(hash_key, name, request.remote_addr)

            print("[ {} ] {}{}register: {}[{}] hash:{}{}{}".format(datetime.now().strftime("%Y%m%d %H:%M:%S"),
                                                                   terminal_bg.BLUE, terminal_fg.WHITE, 
                                                                   name, request.remote_addr, hash_key,
                                                                   terminal_fg.END, terminal_bg.END))
            send_uplink_detection(REGISTER_UPLINK_MSG, name)

            return json.dumps({"id":hash_key,
                               "register_name":name,
                               "status":"OK",
                               "status_code":200})
        else:
            return create_response_403()

class UpdateView(FlaskView):
    database = None

    @classmethod
    def init(cls, database):
        cls.database = database
        cls.client_update = {}

    # filtering
    def before_request_client_get_update(self, name, **kwargs):
        match = re.search(VALID_NETWORK, request.remote_addr)
        if match is None:
            abort(403)

    @route('/host/<string:hash_key>', methods=["POST"])
    def add_data(self, hash_key):
        register_hash_code = request.args.get('token')

        if register_hash_code == TOKEN:
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
        if self.database.host_list[hash_key]["status"] in STATUS_BAD:
            send_uplink_detection(UPDATE_UPLINK_MSG, host_name)
            print("[ {} ] {}{}UP    : {}{}{}".format(datetime.now().strftime("%Y%m%d %H:%M:%S"),
                                                     terminal_bg.GREEN, terminal_fg.BLACK,
                                                     host_name,
                                                     terminal_bg.END, terminal_fg.END))
        else:
            print("[ {} ] UPDATE: {}".format(datetime.now().strftime("%Y%m%d %H:%M:%S"), host_name))

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
                with Timeout(WS_RECEIVE_TIMEOUT, False):
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
    route_base = "/"

    database = None
    term_width = 60

    @classmethod
    def init(cls, database, term_width=60):
        cls.database = database
        cls.term_width = term_width
        cls.env = Environment(loader=FileSystemLoader('.'), trim_blocks=False)

    # filtering
    def before_request(self, name, **kwargs):
        match = re.search(VALID_NETWORK, request.remote_addr)
        if match is None:
            abort(403)

    def page_element(self, host_name):
        fd = self.database.fetch(host_name, return_only_data=True)

        if fd is not None:
            element = render_template('host_entry.tpl', host_name=host_name, host_ip=fd["ip_address"], host_status=fd["status"],
                                      timestamp=fd["data"][0]["timestamp"], gpu_info=fd["data"][0]["gpu_data"], ok_statuses=STATUS_OK)

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

        return render_template('index.html', vesta_version=__version__, title=PAGE_TITLE, description=PAGE_DESCRIPTION,
                               page_num=page_num, total_page=total_page, page_data=fetch_data, ok_statuses=STATUS_OK,
                               server_address=IP, server_port=PORT_NUM)

    def index(self):
        if request.args.get('term', default=False, type=bool):
            # url parameter: page is 0, it means not specified which will fetch all.
            page_num = request.args.get('page', default=0, type=int)

            if page_num < 0:
                return create_response_404("invalid page number.")
            elif page_num == 0:
                fetch_data = self.database.fetch_all(fetch_num=1)

                if request.args.get('detail', default=False, type=bool):
                    response = "vesta ver. {}\n".format(__version__)+format_gpu_detail_info(fetch_data, term_width=self.term_width)
                else:
                    response = "vesta ver. {}\n".format(__version__)+format_gpu_info(fetch_data)
            else:
                fetch_data = self.database.fetch_page(page_num)

                if request.args.get('detail', default=False, type=bool):
                    response = "vesta ver. {}\n".format(__version__)+format_gpu_detail_info(fetch_data, term_width=self.term_width)
                else:
                    response = "vesta ver. {}\n".format(__version__)+format_gpu_info(fetch_data)

            return response
        else:
            if request.args.get('fetch_element', default=False, type=bool):
                return self.page_element(request.args.get('element', default="", type=str))

            return self.page_content(request.args.get('page', default=0, type=int))

class HTTPServer(object):
    def __init__(self, database_name="gpu_states.db", database_dir="data", name="gpu_monitor", bind_host="0.0.0.0",
                       term_width=60, quiet=False):

        # in case it's called from other modules
        self.this_module_path = re.sub("server.py", "", re.sub('\s*File\s"', "", os.path.abspath(__file__)))

        self.database_name = database_name
        self.database_dir = database_dir
        self.name = name
        self.bind_host = bind_host
        self.bind_port = PORT_NUM

        self.main_thread = None
        self.app = Flask(self.name,
                         static_folder=self.this_module_path+"/static",
                         template_folder=self.this_module_path+"/templates")

        # in case it doesn't exist
        mkdir(self.database_dir)
        self.database = DataBase(path_join(self.database_dir, self.database_name))

        MainView.init(self.database, term_width)
        MainView.register(self.app)

        StatesView.init(self.database, term_width)
        StatesView.register(self.app)

        RegisterView.init(self.database)
        RegisterView.register(self.app)

        UpdateView.init(self.database)
        UpdateView.register(self.app)

        self.wsgi_server = pywsgi.WSGIServer((self.bind_host, self.bind_port), self.app, handler_class=WebSocketHandler)

        self.slack_bot = SlackBot(SLACK_BOT_TOKEN, self.database)

        if quiet:
            import logging
            log = logging.getLogger("werkzeug")
            log.disabled = True
            self.app.logger.disabled = True

    def start(self, ssl_context=None):
        # it seems wrapping the flask server working only calling the wsgi_server
        # I will delete this part next release
        #self.main_thread = threading.Thread(target=self.app.run, args=(self.bind_host, self.bind_port), kwargs={"ssl_context":ssl_context})
        self.ws_thread = threading.Thread(target=self.wsgi_server.serve_forever)
        self.bot_thread = threading.Thread(target=self.slack_bot.start)

        #self.main_thread.daemon = True
        #self.main_thread.start()
        self.ws_thread.daemon = True
        self.ws_thread.start()
        self.bot_thread.daemon = True
        self.bot_thread.start()

    def send_down_detection(self, host_name, down_time):
        msg = HOST_DOWN_MSG.format(host_name, down_time)
        
        try:
            resp = requests.post(SLACK_WEBHOOK, data=json.dumps({"text":msg}))
            if resp.history != [] and resp.history != 200:
                print("could not send message to Slack.")
        except Exception as e:
            print(e)

    def send_hosts_statuses(self, msg_title="ALL_HOSTS_STATUSES"):
        msg = ""

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

        if len(msg) > 0:
            self.slack_bot.send_snippet(msg, SLACK_BOT_POST_CHANNEL, msg_title, "statuses")

    def watch_and_sleep(self, sleep_time=1, down_th_sec=60):
        """
            down_th_sec should be set larger number than a interval
            what you are going to send from the host.
        """

        if SCHEDULE_FUNCTION:
            for sche in SCHEDULE_FUNCTION:
                exec(sche)

        while True:
            schedule.run_pending()
            time.sleep(sleep_time)

            for hash_key, host in self.database.host_list.items():
                time_diff = time.time() - host["last_touch"]
                if time_diff > down_th_sec and not host["status"] in STATUS_BAD:
                    self.send_down_detection(host["name"], down_th_sec)
                    self.database.host_list[hash_key]["status"] = SERVER_DOWN
                    print("[ {} ] {}{}DOWN  : {}{}{}".format(datetime.now().strftime("%Y%m%d %H:%M:%S"),
                                                                     terminal_bg.RED, terminal_fg.WHITE, 
                                                                     host["name"],
                                                                     terminal_fg.END, terminal_bg.END))
