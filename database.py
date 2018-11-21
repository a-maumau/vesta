import re
import time
import bz2
import pickle
import sqlite3
from pprint import pprint
from datetime import datetime

BASE_TABLE_NAME = "machines"

SERVER_AVAILABLE = "running"
SERVER_WAITING_UPLINK = "waiting"
SERVER_DOWN = "down"

class DataBase(object):
    def __init__(self, database_path):
        # because of thread safe, it won't allow us to open in advance
        #self.con = sqlite3.connect(database_path)
        #self.cur = self.con.cursor()

        self.database_path = database_path

        self.host_list = {}

        con = sqlite3.connect(self.database_path)
        cur = con.cursor()

        if self.is_machine_table_exist():
            # database is recoreded in each table for each machine,
            # we need the machine list.
            cur.execute("select * from machines;")
            result = cur.fetchall()
            for data in result:
                #{hash key: host_name}
                self.host_list[data[0]] = {"name":data[1], "last_update":time.time(), "status":SERVER_WAITING_UPLINK}
            
            print("#### database ####")
            pprint(self.host_list)
        else:
            self.init_database()

        con.close()

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

        # if table doesn't exist it will return empty list
        if cur.fetchall() != []:
            con.close()
            return True
        else:
            con.close()
            return False

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
        response = {}

        con = sqlite3.connect(self.database_path)
        cur = con.cursor()

        query = "select name from sqlite_master where type='table';"
        cur.execute(query)
        # output of cur.fetchall() is like [(table1, ), (table2, ), ...]
        table_list = list(map(lambda x: x[0], cur.fetchall()))

        for host in self.host_list.values():
            host_name = host["name"]
            if host_name in table_list:
                query = "select * from {} order by timestamp desc limit {};".format(host_name, fetch_num)
                cur.execute(query)

                result = cur.fetchall()

                if len(result) != 0:
                    response[host_name] = []
                    for data in result[::-1]:
                        record = self.expand_data(data[1])
                        record["timestamp"] = data[0]
                        response[host_name].append(record)

        con.close()

        return response

    def fetch(self, host_name, fetch_num=1):
        response = {}

        con = sqlite3.connect(self.database_path)
        cur = con.cursor()

        query = "select * from {} order by timestamp desc limit {};".format(host_name, fetch_num)
        cur.execute(query)

        result = cur.fetchall()

        if len(result) != 0:
            response[host_name] = []
            for data in result[::-1]:
                response[host_name].append(self.expand_data(data[1]))

        con.close()

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
        self.host_list[host_id] = {"name":host_name, "last_update":time.time(), "status":SERVER_AVAILABLE}
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
