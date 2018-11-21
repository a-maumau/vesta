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

from flask import Flask, render_template, redirect, request, abort
from flask_classful import FlaskView, route

import database
from settings import *
from path_util import *

def create_response_403(info_msg="forbidden"):
    return json.dumps({"status":"ERROR", "status_code":403, "info":"{}".format(info_msg)})

def create_response_404(info_msg="not found"):
    return json.dumps({"status":"ERROR", "status_code":404, "info":"{}".format(info_msg)})

def send_uplink_detection(msg, host_name):
    try:
        resp = requests.post(SLACK_WEBHOOK, data=json.dumps({"text":msg.format(host_name)}))
    except:
        pass

def align_str(text, fill_char=" ", margin_char=" ", margin=(1,1), length=60, start=4, ellipsis="...", new_line=True):
    margin_start_pos = max(0, start-margin[0])

    if len(text)+margin_start_pos >= length:
        text = text[margin_start_pos:length-len(ellipsis)-1]+ellipsis

    text_end_pos = margin_start_pos+len(text)
    suf_margin_pos = min(margin[1], length-text_end_pos)

    arg = {
            "pre_fill_str"   : fill_char*(margin_start_pos),
            "pre_margin_str" : margin_char*margin[0],
            "text"           : text,
            "suf_margin_str" : margin_char*suf_margin_pos,
            "suf_fill_str"   : fill_char*max(0, length-suf_margin_pos-text_end_pos),
            "new_line"       : "\n" if new_line else ""
           }

    return "{pre_fill_str}{pre_margin_str}{text}{suf_margin_str}{suf_fill_str}{new_line}".format(**arg)

def create_bar_str(current, total, msg="", fill_char="/", empty_char=" ", left_bracket="[", right_bracket="]", length=60, new_line=True):
    bar_len = length-len(left_bracket)-len(right_bracket)-len(" ddd%")-len(msg)
    fill_num = int((current/total)*bar_len)
    percent = int((current/total)*100)

    return "{}{}{}{}{} {: 3d}%{}".format(
            msg, left_bracket, fill_char*fill_num, empty_char*(bar_len-fill_num), right_bracket, percent, "\n" if new_line else "")

def trucate_str(text, length=25, fill_char=None, ellipsis="...", new_line=True):
    if len(text) > length:
        return text[:length-len(ellipsis)]+ellipsis
    elif fill_char is not None:
        return "{}{}".format(text, fill_char*(length-len(text)))
    else:
        return text

"""
# this part is not looking good... should be merged?

database = None

@classmethod
def set_database(cls, database):
    cls.database = database
"""

"""
    fetched data will be like            
    "host1":[
        {'gpu:0': {'available_memory': '10952',
               'device_num': '0',
               'gpu_name': 'GeForce GTX 1080 Ti',
               'gpu_volatile': '0',
               'processes': [{'pid': 1963,
                              'name': '/usr/bin/X',
                              'used_memory': '133'},
                             {'pid': 3437,
                              'name': 'compiz',
                              'used_memory': '81'}],
               'temperature': '38',
               'timestamp': '2018/11/05 12:24:24.111',
               'total_memory': '11169',
               'used_memory': '217',
               'uuid': 'GPU-...'},
        'gpu:1': {'available_memory': '11170',
               'device_num': '1',
               'gpu_name': 'GeForce GTX 1080 Ti',
               'gpu_volatile': '0',
               'processes': [],
               'temperature': '40',
               'timestamp': '2018/11/05 12:24:24.113',
               'total_memory': '11172',
               'used_memory': '2',
               'uuid': 'GPU-...'}}
    ]
"""

class StatesView(FlaskView):
    database = None

    @classmethod
    def set_database(cls, database):
        cls.database = database

    # filtering
    def before_request(self, name, **kwargs):
        match = re.search(VALID_NETWORK, request.remote_addr)
        if match is None:
            abort(403)

    @route('/')
    def all_status(self):
        fetch_num = request.args.get('fetch_num', default=1, type=int)
        fetch_data = self.database.fetch_all(fetch_num=fetch_num)

        return json.dumps(fetch_data)

    @route('/<string:host_name>/')
    def host_status(self, host_name):
        if self.database.has_host(host_name):
            fetch_num = request.args.get('fetch_num', default=1, type=int)
            fetch_data = self.database.fetch(host_name, fetch_num=fetch_num)

            return json.dumps(fetch_data)
        else:
            return create_response_404("not found")

class RegisterView(FlaskView):
    database = None

    @classmethod
    def set_database(cls, database):
        cls.database = database

    def send_uplink_detection(self, host_name):
        msg = REGISTER_UPLINK_MSG.format(host_name)
        try:
            resp = requests.post(SLACK_WEBHOOK, data=json.dumps({"text":msg}))
        except:
            pass

    @route('/', methods=["GET"])
    def rergister(self):
        # for avoiding error in sqlite3, I think there is more token cause error...
        name = request.args.get('host_name').replace(".", "_").replace(",", "_").replace("-", "_").replace("@", "_")
        name = name.replace("[", "_").replace("]", "_").replace(":", "_").replace(";", "_")
        register_hash_code = request.args.get('token')

        if register_hash_code == TOKEN:
            hash_code = random.getrandbits(128)
            hash_key = "{:x}".format(hash_code)

            if self.database.has_host(name):
                additional_name_hash = random.getrandbits(32)
                name = "{}_{:x}".format(name, additional_name_hash)

            self.database.add_host(hash_key, name, request.remote_addr)

            print("### register: {} hash:{} ###".format(name, hash_key))
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
    def set_database(cls, database):
        cls.database = database

    @route('/<string:hash_key>', methods=["POST"])
    def add_data(self, hash_key):
        register_hash_code = request.args.get('token')

        if register_hash_code == TOKEN:
            if self.database.has_hash(hash_key):
                poseted_data = request.get_json()

                if self.database.host_list[hash_key]["status"] in STATUS_BAD:
                    send_uplink_detection(UPDATE_UPLINK_MSG, self.database.host_list[hash_key]["name"])

                self.database.add_data(hash_key, poseted_data)
                self.database.host_list[hash_key]["status"] = SERVER_AVAILABLE
                self.database.host_list[hash_key]["last_update"] = time.time()

                return json.dumps({"status":"OK", "status_code":200})
            else:
                return create_response_404("not in known list")
        else:
            return create_response_403()

class MainView(FlaskView):
    route_base = "/"
    database = None

    @classmethod
    def set_database(cls, database):
        cls.database = database

    def index(self):
        if request.args.get('term', default=False, type=bool):
            fetch_data = self.database.fetch_all(fetch_num=1)

            response = ""
            for host, v_array in fetch_data.items():
                if v_array != []:
                    data = v_array[0]
                    response += "\n"+align_str(host, fill_char="#", margin_char=" ", margin=(1,1), start=4)

                    for gpu, status in data.items():
                        response += "[{}]\n".format(gpu)
                        response += "temperature      memory used  memory available  gpu volatile\n"
                        response += "       {: 3d}℃  {: 5d}/{: 5d}MiB         {: 5d}MiB          {: 3d}%\n".format(
                                     int(status['temperature']), int(status['used_memory']), int(status['total_memory']),
                                     int(status['available_memory']), int(status['gpu_volatile']))
                        response += create_bar_str(current=int(status['used_memory']), total=int(status['total_memory']), msg="mem")

                        for index, process_data in enumerate(status["processes"]):
                            if index == len(status["processes"])-1:
                                response += "└── {} {: 5d}MiB\n".format(trucate_str(process_data['name'], fill_char=" "), int(process_data['used_memory']))
                            else:
                                response += "├── {} {: 5d}MiB\n".format(trucate_str(process_data['name'], fill_char=" "), int(process_data['used_memory']))

                        response += "\n"

            return response
        else:
            return render_template('index.html', title='main')

class HTTPServer(object):
    def __init__(self, database_name="gpu_states.db", database_dir="data", name="gpu_monitor", bind_host="0.0.0.0", quiet=False):
        self.this_module_path = re.sub("gpu_status_server.py", "", re.sub('\s*File\s"', "", os.path.abspath(__file__)))
        self.database_name = database_name
        self.database_dir = database_dir
        self.name = name
        self.bind_host = bind_host
        self.bind_port = PORT_NUM

        self.main_thread = None
        self.app = Flask(self.name, static_folder=self.this_module_path+"/static", template_folder=self.this_module_path+"/templates")

        # in case it doesn't exist
        mkdir(self.database_dir)
        self.database = database.DataBase(path_join(self.database_dir, self.database_name))

        MainView.set_database(self.database)
        MainView.register(self.app)

        StatesView.set_database(self.database)
        StatesView.register(self.app)

        RegisterView.set_database(self.database)
        RegisterView.register(self.app)

        UpdateView.set_database(self.database)
        UpdateView.register(self.app)

        if quiet:
            import logging
            log = logging.getLogger("werkzeug")
            log.disabled = True
            self.app.logger.disabled = True

    def start(self):
        self.main_thread = threading.Thread(target=self.app.run, args=(self.bind_host, self.bind_port))
        self.main_thread.daemon = True
        self.main_thread.start()

    def send_down_detection(self, host_name, down_time):
        msg = HOST_DOWN_MSG.format(host_name, down_time)
        try:
            resp = requests.post(SLACK_WEBHOOK, data=json.dumps({"text":msg}))
        except:
            pass

    def send_server_status(self):
        msg = "### Server Statuses ###\n"

        for hash_key, host in self.database.host_list.items():
            msg += "{} : {}\n".format(host["name"], "`Dead`" if host["status"] in STATUS_BAD else "Alive")

        resp = requests.post(SLACK_WEBHOOK, data=json.dumps({"text":msg}))

    def watch_and_sleep(self, sleep_time=2, down_th_sec=300):
        if SCHEDULE_FUNCTION:
            exec(SCHEDULE_FUNCTION)

        while True:
            schedule.run_pending()
            time.sleep(sleep_time)

            for hash_key, host in self.database.host_list.items():
                time_diff = time.time() - host["last_update"]
                if time_diff > down_th_sec and not host["status"] in STATUS_BAD:
                    self.send_down_detection(host["name"], down_th_sec)
                    self.database.host_list[hash_key]["status"] = SERVER_DOWN

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    # args for server
    parser.add_argument('--db_name', type=str, default="gpu_states.db", help='')
    parser.add_argument('--db_dir', type=str, default="data", help='in sec')
    parser.add_argument('--server_name', type=str, default="gpu_monitor", help='in sec')
    parser.add_argument('--bind_host', type=str, default="0.0.0.0", help='in sec')
    # for bind post, please change PORT_NUM in settings.

    # args for waching part
    parser.add_argument('--sleep_time', type=int, default=10, help='')
    parser.add_argument('--down_th', type=int, default=300, help='in sec')

    parser.add_argument('-quiet', action="store_true", default=False, help='only showing the log of loss and validation')

    args = parser.parse_args()

    server = HTTPServer(database_name=args.db_name, database_dir=args.db_dir, name=args.server_name, quiet=args.quiet)
    server.start()
    server.watch_and_sleep(args.sleep_time, args.down_th)
