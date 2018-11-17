import os
import re
import json
import yaml
import requests
import argparse
import subprocess

#from settings import *
#from path_util import *

GPU_QUERY = [#  (query, alias)
              ('index', "device_num"),       # this must come first
               ('uuid', "uuid"),             #
               ('name', "gpu_name"),         #
    ('temperature.gpu', "temperature"),      # in celsius
       ('memory.total', "total_memory"),     # in MiB
        ('memory.free', "available_memory"), # in MiB
        ('memory.used', "used_memory"),      # in MiB
          ('timestamp', "timestamp"),        #
    ('utilization.gpu', "gpu_volatile")      # in percentage
]

def get_gpu_info(nvidia_smi='nvidia-smi'):
    """
        example output of this function

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
    """

    # for me
    """
        about bus id `GPU 00000000:01:00.0`
        this thing looks to be varying in some kind of hardware setting.
        sometimes, machine only have 2 GPUs, but the `bus id` starts from like `00000000:03:00.0`.
        so parsing `nvidia-smi -q -d PID` directly somtimes cause trouble.

        the bus id itsself is `domain:bus:device.function` in hex.
        (https://nvidia.custhelp.com/app/answers/detail/a_id/3751/~/useful-nvidia-smi-queries)

        to parse the running process on GPU, there are two ways.
        1.
            use `nvidia-smi --query-gpu=index,pci.bus_id --format=csv` command
            and construct the mapping between `index` and `bus id`
            output of the command is like
                `0, 00000000:01:00.0`

        2.
            parse the `nvidia-smi` command output like
            `nvidia-smi | awk '$2=="Processes:" {p=1} p && $2 == 0 && $3 > 0 {print $2,$3,$5,$6}'`
            output of above command is like
                `0 30348 python 3679MiB`
            this way is easier, I think, but it really depends on the format of nvidia-smi.

        at this time, I chose 2.
    """

    gpu_info_dict = {}

    # get gpu status ######################################################################
    query_list = list(map(lambda x: x[0], GPU_QUERY))
    alias_list = list(map(lambda x: x[1], GPU_QUERY))

    # nounits means no % or MiB or so on
    cmd = '{} --query-gpu={} --format=csv,noheader,nounits'.format(nvidia_smi, ','.join(query_list))
    output = subprocess.check_output(cmd, shell=True).decode("utf-8")
    lines = output.split('\n')
    lines = [ line.strip() for line in lines if line.strip() != '' ]

    for line in lines:
        line = line.split(", ")
        gpu_info_dict["gpu:{}".format(line[0])] = { k: v for k, v in zip(alias_list+["processes"], line+[[]])}

    # get gpu processes ##################################################################
    cmd = "nvidia-smi | awk '$2==\"Processes:\" {{p=1}} p && $2 == 0 && $3 > 0 {{print $2,$3,$5,$6}}'".format(nvidia_smi)
    output = subprocess.check_output(cmd, shell=True).decode("utf-8")
    lines = output.split('\n')
    lines = [ line.strip().split(" ") for line in lines if line.strip() != '' ]

    for line in lines:
        # each line will have ["gpu index", "pid", "command", "Used memory"]
        gpu_info_dict["gpu:{}".format(line[0])]["processes"].append({"pid":line[1], "name":line[2], "used_memory":line[3].replace("MiB", "")})
    
    return gpu_info_dict

def register(yaml_path):
    host_name = os.uname()[1]

    resp = requests.get("http://{}:{}/register/?host_name={}&token={}".format(IP, PORT_NUM, host_name, TOKEN))
    if resp.status_code == requests.codes.ok:
        resp_dict = resp.json()
        if resp_dict["status_code"] == 200:
            # it will returns like
            # {'id': 'f77818f42cabfdf1358250463a2db3d6', 'register_name': 'script_test', 'status': 'OK', 'status_code': 200}

            with open(yaml_path, "w") as yaml_writer:
                yaml_writer.write(yaml.dump({"hash_key":resp_dict["id"], "registered_name":resp_dict["register_name"]}, default_flow_style=False))

            return resp_dict["id"]
    
    exit(1)

def post_data(token, yaml_path):
    content = get_gpu_info()

    resp = requests.post("http://{}:{}/update/{}?token={}".format(IP, PORT_NUM, token, TOKEN), data=json.dumps(content), headers={'Content-Type': 'application/json'})
    if resp.status_code == requests.codes.ok:
        resp_dict = resp.json()

        # in case server has initialized the database
        if resp_dict["status_code"] == 404:
            token = register(yaml_path)
            resp = requests.post("http://{}:{}/update/{}?token={}".format(IP, PORT_NUM, token, TOKEN), data=json.dumps(content), headers={'Content-Type': 'application/json'})

def main(token_yaml_name="token", yaml_dir="data", nvidia_smi="nvidia-smi"):
    yaml_path = path_join(yaml_dir, token_yaml_name+".yaml")

    # in case it does not exist
    mkdir(yaml_dir)
    if path_exist(yaml_path):
        with open(yaml_path, "r") as f:
            yaml_data = yaml.load(f)
            if yaml_data is not None:
                token = yaml_data["hash_key"]
            else:
                token = register(yaml_path)
    else:
        token = register(yaml_path)

    post_data(token, yaml_path)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('--yaml_dir', type=str, default="data", help='the dir of yaml which token is saved.')
    parser.add_argument('--yaml_name', type=str, default="yaml", help='path of yaml file.')
    parser.add_argument('--nvidia-smi', type=str, default="nvidia-smi", help='if you want to specify nvidia-smi command.')

    args = parser.parse_args()
    
    main(args.yaml_name, args.yaml_dir, args.nvidia_smi)
