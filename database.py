import re
import time
import bz2
import pickle
import sqlite3
import collections as cl
from pprint import pprint
from datetime import datetime

from env import *
from settings import *

BASE_TABLE_NAME = "machines"

class DataBase(object):
    def __init__(self, database_path, sort_by="ip"):
        # because of thread safe, it won't allow us to open in advance
        #self.con = sqlite3.connect(database_path)
        #self.cur = self.con.cursor()

        self.database_path = database_path
        self.host_list = {}
        self.name_to_hash_table = {}

        # sort for paging, this is not appropriate way if hosts are large number
        # host list is like {"host_hash":{"name":"host1". "ip_address":"192.168.0.1", ...}, {...}, }
        if sort_by == "ip":
            self.sort_func = lambda d: list(map(lambda t: t[0], sorted(d.items(), key=lambda t: t[1]["ip_address"])))
        else:
            self.sort_func = lambda d: list(map(lambda t: t[0], sorted(d.items(), key=lambda t: t[1]["name"])))

        con = sqlite3.connect(self.database_path)
        cur = con.cursor()

        if self.is_machine_table_exist():
            # database is recoreded in each table for each machine,
            # we need the machine list.
            cur.execute("select * from machines;")
            result = cur.fetchall()
            for data in result:
                #{hash key: host_name}
                self.host_list[data[0]] = {"name":data[1], "ip_address":data[2], "last_update":time.time(), "status":SERVER_WAITING_UPLINK}
                self.name_to_hash_table[data[1]] = data[0]
            
            print("#### database ####")
            pprint(self.host_list)
        else:
            self.init_database()

        con.close()

        # host_order has the keys (host_name) in list.
        self.host_order = self.sort_func(self.host_list)

    @property
    def total_page(self):
        return (len(self.host_order)//PAGE_PER_HOST_NUM) + 1 if len(self.host_order)%PAGE_PER_HOST_NUM != 0 else 0

    def name_to_hash(self, host_name):
        if host_name in self.name_to_hash_table:
            return self.name_to_hash_table[host_name]

        return ""

    def get_page_host_names(self, page_num):
        return list(map(lambda x: self.host_list[x]["name"], self.host_order[PAGE_PER_HOST_NUM*(page_num-1):PAGE_PER_HOST_NUM*page_num]))

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

    def format_timestamp(self, ts):
        # ex. 20181123204514 -> 2018/11/23 20:45:14
        ts = str(ts)

        return "{}/{}/{} {}:{}:{}".format(ts[0:4], ts[4:6], ts[6:8], ts[8:10], ts[10:12], ts[12:14])

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

                response[host_name] = {"data":[],
                                       "ip_address":self.host_list[self.name_to_hash_table[host_name]]["ip_address"],
                                       "status":self.host_list[self.name_to_hash_table[host_name]]["status"]}

                if len(result) != 0:
                    if self.host_list[self.name_to_hash_table[host_name]]["status"] in STATUS_BAD:
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

    def fetch_page(self, page_num):
        """
            returns a each page data.
        """

        fetch_data = cl.OrderedDict()

        for host_hash in self.host_order[PAGE_PER_HOST_NUM*(page_num-1):PAGE_PER_HOST_NUM*page_num]:
            host_name = self.host_list[host_hash]["name"]

            # {"host_name":{"data":[...], "ip_address", "status":"running"}, ...}
            fetch_data[host_name] = self.fetch(host_name, fetch_num=1)[host_name]

        return fetch_data

    def fetch(self, host_name, fetch_num=1, return_only_data=False):
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

        response = {}

        con = sqlite3.connect(self.database_path)
        cur = con.cursor()

        query = "select * from {} order by timestamp desc limit {};".format(host_name, fetch_num)
        cur.execute(query)

        result = cur.fetchall()

        response[host_name] = {"data":[],
                               "ip_address":self.host_list[self.name_to_hash_table[host_name]]["ip_address"],
                               "status":self.host_list[self.name_to_hash_table[host_name]]["status"]}

        if len(result) != 0:
            if self.host_list[self.name_to_hash_table[host_name]]["status"] in STATUS_BAD:
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

    def has_hash(self, hash_key):
        if hash_key in self.host_list:
            return True
        else:
            return False

    def has_host(self, host_name):
        if host_name in list(map(lambda x: x["name"], self.host_list.values())) or host_name is "machines":
            return True
        else:
            return False

    def add_host(self, host_id, host_name, host_ip):
        self.host_list[host_id] = {"name":host_name, "ip_address":host_ip, "last_update":time.time(), "status":SERVER_AVAILABLE}
        self.name_to_hash_table[host_name]= host_id
        self.host_order = self.sort_func(self.host_list)
        self.create_new_host(host_id, host_name, host_ip)

    def add_data(self, host_id, data):
        con = sqlite3.connect(self.database_path)
        cur = con.cursor()

        cur.execute("insert into {} values(:timestamp, :data)".format(self.host_list[host_id]["name"]),
                    {"timestamp":"{}".format(int(datetime.now().strftime("%Y%m%d%H%M%S"))), "data":self.compress_data(data)})

        con.commit()
        con.close()

    def compress_data(self, data):
        return bz2.compress(pickle.dumps(data, pickle.HIGHEST_PROTOCOL))

    def expand_data(self, data):
        return pickle.loads(bz2.decompress(data)) 
