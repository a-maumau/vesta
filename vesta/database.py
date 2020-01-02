import re
import time
import bz2
import pickle
import sqlite3
import collections as cl
from pprint import pprint
from datetime import datetime

from . import env

BASE_TABLE_NAME = "machines"

class Database(object):
    """
        takes care of sqlite3 database
    """
    
    def __init__(self, settings, database_path):
        """ 
            args:
                settings
                    settings must have following instance variable
                        TOKEN                                   :str
                        PAGE_PER_HOST_NUM                       :int
                        TIMESTAMP_FORMAT                        :str -> choice ['YMD', 'MDY', 'DMY']
                        SORT_BY                                 :str
                        SAVE_INTERVAL                           :int
                        QUIET                                   :bool

                    typically, I recommend using `argparse`.
                    see `gpu_status_server.py` for more detail.

                database_path: str
                    path to sqlite3 file.
        """

        self.settings = settings
        self.database_path = database_path

        # host_list will be like
        """
        {   
            "host1":{
                "name":"host1",                 # str
                "ip_address":"127.0.0.2",       # str
                "last_update":0,                # float
                "last_touch":0,                 # float, use for detecting down
                "status":SERVER_WAITING_UPLINK  # str
            },
        }

        it's not a `list`, it's a `dict`...
        """
        self.host_list = {}
        self.name_to_hash_table = {}

        # sort for paging, this is not appropriate way if hosts are large number
        # host list is like {"host_hash":{"name":"host1". "ip_address":"192.168.0.1", ...}, {...}, }
        if self.settings.SORT_BY.lower() in ["ip", "ipaddress", "ip_address", "address"]:
            self.sort_func = lambda d: list(map(lambda t: t[0], sorted(d.items(), key=lambda t: t[1]["ip_address"])))
        else:
            self.sort_func = lambda d: list(map(lambda t: t[0], sorted(d.items(), key=lambda t: t[1]["name"])))

        con = sqlite3.connect(self.database_path)
        cur = con.cursor()

        if self.is_machine_table_exist():
            # data is recoreded in each table for each machine,
            # we need the machine list.
            cur.execute("select * from machines;")
            result = cur.fetchall()
            for data in result:
                # {hash key: host_name}, "last_update" and "last_touch" are unix time (sec)
                self.host_list[data[0]] = {"name":data[1], "ip_address":data[2], "last_update":0, "last_touch":0,
                                           "status":env.SERVER_WAITING_UPLINK, "cache_data":None}
                self.name_to_hash_table[data[1]] = data[0]
            
            print("#### database ####")
            pprint(self.host_list)
        else:
            self.init_database()

        con.close()

        # host_order has the keys (host_name) in list.
        self.host_order = self.sort_func(self.host_list)

        self.ts_format = self.settings.TIMESTAMP_FORMAT.lower()

    @property
    def total_page(self):
        return (len(self.host_order)//self.settings.PAGE_PER_HOST_NUM) + 1 if len(self.host_order)%self.settings.PAGE_PER_HOST_NUM != 0 else 0

    def name_to_hash(self, host_name):
        if host_name in self.name_to_hash_table:
            return self.name_to_hash_table[host_name]

        return ""

    def get_page_host_names(self, page_num):
        return list(map(lambda x: self.host_list[x]["name"], self.host_order[self.settings.PAGE_PER_HOST_NUM*(page_num-1):self.settings.PAGE_PER_HOST_NUM*page_num]))

    def init_database(self):
        con = sqlite3.connect(self.database_path)
        cur = con.cursor()

        create_table_query = "create table machines (id TEXT, name TEXT, ip_address TEXT)"
        cur.execute(create_table_query)
        con.commit()
        con.close()

    def is_machine_table_exist(self):
        con = sqlite3.connect(self.database_path)
        cur = con.cursor()

        create_table_query = "select name from sqlite_master where type='table' and name='{}';".format(BASE_TABLE_NAME)
        cur.execute(create_table_query)

        # if table doesn't exist, it will return empty list
        if cur.fetchall() != []:
            con.close()
            return True
        else:
            con.close()
            return False

    def get_timestamp(self):
        """
            return a timestamp string.

            return: str
                it is like "201801010000" which is "YYYYMMDDhhmmss" style.
        """

        return datetime.now().strftime("%Y%m%d%H%M%S")

    def get_unix_timestamp(self):
        return time.time()

    def format_timestamp(self, ts):
        """
            return a formatted timestamp string.

            return: str
                it is like "01/01/2018 00:00:00".
                you can change the format by changing the self.ts_format
        """

        ts = str(ts)

        # ex. 20181123204514 -> 2018/11/23 20:45:14
        if self.ts_format == "ymd":
            return "{}/{}/{} {}:{}:{}".format(ts[0:4], ts[4:6], ts[6:8], ts[8:10], ts[10:12], ts[12:14])

        # ex. 20181123204514 -> 11/23/2018 20:45:14
        if self.ts_format == "mdy":
            return "{}/{}/{} {}:{}:{}".format(ts[4:6], ts[6:8], ts[0:4], ts[8:10], ts[10:12], ts[12:14])

        # ex. 20181123204514 -> 23/11/2018 20:45:14
        if self.ts_format == "dmy":
            return "{}/{}/{} {}:{}:{}".format(ts[6:8], ts[4:6], ts[0:4], ts[8:10], ts[10:12], ts[12:14])

        return "{}/{}/{} {}:{}:{}".format(ts[4:6], ts[6:8], ts[0:4], ts[8:10], ts[10:12], ts[12:14])

    def format_unix_timestamp(self, uinx_ts):
        """
            return a formatted timestamp string of unix time.

            return: str
                it is like "01/01/2018 00:00:00".
                you can change the format by changing the self.ts_format
        """

        ts = datetime.fromtimestamp(uinx_ts)

        # ex. 2018/11/23 20:45:14
        if self.ts_format == "ymd":
            return ts.strftime('%Y/%m/%d %H:%M:%S')

        # ex. 11/23/2018 20:45:14
        if self.ts_format == "mdy":
            return ts.strftime('%m/%d/%Y %H:%M:%S')

        # ex. 23/11/2018 20:45:14
        if self.ts_format == "dmy":
            return ts.strftime('%d/%m/%Y %H:%M:%S')

        return ts.strftime('%m/%d/%Y %H:%M:%S')

    def convert_unix_timestamp_to_timestamp(self, uinx_ts):
        """
            convert unix time to timestamp

            return: str
                it is like "20180101182307", YYYYDDMMhhmmss style.
        """

        ts = datetime.datetime.fromtimestamp(uinx_ts)

        return int(ts.strftime('%Y%m%d%H%M%S'))

    def create_new_host(self, host_id, host_name, host_ip):
        con = sqlite3.connect(self.database_path)
        cur = con.cursor()

        create_table_query = "create table {} (timestamp INTEGER, data BLOB)".format(host_name)
        cur.execute(create_table_query)
        cur.execute("insert into machines values(:id, :name, :ip_address)",
                    {"id":host_id, "name":host_name, "ip_address":host_ip})

        con.commit()
        con.close()

    def fetch_all(self, fetch_num=1):
        """
            return all host's gpu information data with list of dictionary.

            args:
                host_name: str
                fetch_num: int

            return: dict
                it will return fetch_num of data for each host
        """

        response = {}

        con = sqlite3.connect(self.database_path)
        cur = con.cursor()

        query = "select name from sqlite_master where type='table';"
        cur.execute(query)
        # output of cur.fetchall() is like [(table1, ), (table2, ), ...]
        table_list = list(map(lambda x: x[0], cur.fetchall()))

        for host_name in list(map(lambda x: self.host_list[x]["name"], self.host_order)):
            if host_name in table_list:
                query = "select * from {} order by timestamp desc limit {};".format(host_name, fetch_num)
                cur.execute(query)

                result = cur.fetchall()

                host_id = self.name_to_hash_table[host_name]

                response[host_name] = {"data":[],
                                       "ip_address":self.host_list[host_id]["ip_address"],
                                       "status":self.host_list[host_id]["status"]}

                if len(result) != 0:
                    if self.host_list[host_id]["status"] in env.STATUS_BAD:
                        response[host_name]["data"].append({"gpu_data":{}, "timestamp":self.format_timestamp(result[0][0])})
                    else:
                        for data in result[::-1]:
                            """
                                each data will be
                                "host_name"{
                                    "data":[
                                        {
                                            gpu_data":{< gpu information which is sended by host>},
                                            "timestamp": 201801010000, # which is in server timezone
                                        },
                                        {...},
                                        .
                                        .
                                        .
                                    ],
                                    "ip_address": "< server ip address >"
                                }
                            """
                            response[host_name]["data"].append({"gpu_data": self.expand_data(data[1]),
                                                                "timestamp":self.format_timestamp(data[0])})
                else:
                    response[host_name]["data"].append({"gpu_data":{}, "timestamp":"no entry received."})

        con.close()

        return response

    def fetch_all_cache(self):
        """
            return all host's gpu information data with list of dictionary.

            args:
                host_name: str
                fetch_num: int

            return: dict
                it will return fetch_num of data for each host
        """

        response = {}

        for host_id in self.host_order:
            host_name = self.host_list[host_id]["name"]

            response[host_name] = {"data":[],
                                   "ip_address":self.host_list[host_id]["ip_address"],
                                   "status":self.host_list[host_id]["status"]}

            if self.host_list[host_id]["cache_data"] is None:
                response[host_name]["data"].append({"gpu_data":{}, "timestamp":"no entry received."})
            else:
                if self.host_list[host_id]["status"] in env.STATUS_BAD:
                    response[host_name]["data"].append({"gpu_data":{}, "timestamp":self.format_unix_timestamp(self.host_list[host_id]["last_touch"])})
                else:
                    response[host_name]["data"].append({"gpu_data":self.host_list[host_id]["cache_data"]["data"],
                                                        "timestamp":self.format_timestamp(self.host_list[host_id]["cache_data"]["timestamp"])})

        return response

    def fetch_page(self, page_num):
        """
            returns a each page data.
        """

        fetch_data = cl.OrderedDict()

        for host_hash in self.host_order[self.settings.PAGE_PER_HOST_NUM*(page_num-1):self.settings.PAGE_PER_HOST_NUM*page_num]:
            host_name = self.host_list[host_hash]["name"]

            # {"host_name":{"data":[...], "ip_address", "status":"running"}, ...}
            fetch_data[host_name] = self.fetch(host_name, fetch_num=1)[host_name]

        return fetch_data

    def fetch(self, host_name, fetch_num=1, return_only_data=False, ignore_down_state=False):
        """
            return a host's gpu information data with dictionary.

            args:
                host_name: str
                fetch_num: int

            return: dict
                it will return fetch_num of data for host_name.
        """

        if host_name not in self.name_to_hash_table:
            return None

        host_id = self.name_to_hash_table[host_name]

        response = {}

        con = sqlite3.connect(self.database_path)
        cur = con.cursor()

        query = "select * from {} order by timestamp desc limit {};".format(host_name, fetch_num)
        cur.execute(query)

        result = cur.fetchall()

        response[host_name] = {"data":[],
                               "ip_address":self.host_list[host_id]["ip_address"],
                               "status":self.host_list[host_id]["status"]}

        if len(result) != 0:
            if self.host_list[host_id]["status"] in env.STATUS_BAD and not ignore_down_state:
                response[host_name]["data"].append({"gpu_data":{}, "timestamp":self.format_timestamp(result[0][0])})
            else:
                for data in result[::-1]:
                    """
                        each data will be
                        "host_name"{
                            "data":[
                                {
                                    gpu_data":{< gpu information which is sended by host>},
                                    "timestamp": 201801010000, # which is in server timezone
                                },
                                {...},
                                .
                                .
                                .
                            ],
                            "ip_address": "< server ip address >"
                        }
                    """

                    response[host_name]["data"].append({"gpu_data":self.expand_data(data[1]),
                                                        "timestamp":self.format_timestamp(data[0])})
        else:
            response[host_name]["data"].append({"gpu_data":{}, "timestamp":"no entry received."})

        con.close()

        if return_only_data:
            return response[host_name]

        return response

    def fetch_cache(self, host_name, return_only_data=False):
        """
            return a host's gpu information data with dictionary.

            args:
                host_name: str
                fetch_num: int

            return: dict
                it will return cached data for host_name.
        """

        if host_name not in self.name_to_hash_table:
            return None

        host_id = self.name_to_hash_table[host_name]

        response = {}
        response[host_name] = {"data":[],
                               "ip_address":self.host_list[host_id]["ip_address"],
                               "status":self.host_list[host_id]["status"]}

        if self.host_list[host_id]["cache_data"] is None:
            response[host_name]["data"].append({"gpu_data":{}, "timestamp":"no entry received."})
        else:
            if self.host_list[host_id]["status"] in env.STATUS_BAD:
                response[host_name]["data"].append({"gpu_data":{}, "timestamp":self.format_unix_timestamp(self.host_list[host_id]["last_update"])})
            else:
                response[host_name]["data"].append({"gpu_data":self.host_list[host_id]["cache_data"]["data"],
                                                    "timestamp":self.format_timestamp(self.host_list[host_id]["cache_data"]["timestamp"])})

        if return_only_data:
            return response[host_name]

        return response

    def has_hash(self, hash_key):
        if hash_key in self.host_list:
            return True
        else:
            return False

    def has_host(self, host_name):
        if host_name in self.name_to_hash_table:
            return True
        else:
            return False

    def add_host(self, host_id, host_name, host_ip):
        unix_ts = self.get_unix_timestamp()-self.settings.SAVE_INTERVAL
        self.host_list[host_id] = {"name":host_name, "ip_address":host_ip, "last_update":unix_ts, "last_touch":unix_ts,
                                   "status":env.SERVER_AVAILABLE, "cache_data":None}
        self.name_to_hash_table[host_name] = host_id
        self.host_order = self.sort_func(self.host_list)
        self.create_new_host(host_id, host_name, host_ip)

    def add_data(self, host_id, data):
        ts = int(self.get_timestamp())
        unix_ts = self.get_unix_timestamp()

        self.host_list[host_id]["status"] = env.SERVER_AVAILABLE
        self.host_list[host_id]["last_touch"] = unix_ts
        self.host_list[host_id]["cache_data"] = {"timestamp":ts, "data":data}

        if self.get_unix_timestamp() - self.host_list[host_id]["last_update"] >= self.settings.SAVE_INTERVAL:
            self.host_list[host_id]["last_update"] = unix_ts

            con = sqlite3.connect(self.database_path)
            cur = con.cursor()

            cur.execute("insert into {} values(:timestamp, :data)".format(self.host_list[host_id]["name"]),
                        {"timestamp":ts, "data":self.compress_data(data)})

            con.commit()
            con.close()

    def touch_data(self, host_id):
        self.host_list[host_id]["last_touch"] = self.get_unix_timestamp()

    def compress_data(self, data):
        return bz2.compress(pickle.dumps(data, pickle.HIGHEST_PROTOCOL))

    def expand_data(self, data):
        return pickle.loads(bz2.decompress(data))
