import os
import re
import json
import yaml
import requests
import subprocess
import collections as cl

from .path_util import *

# gpu queries.
# see the help by `nvidia-smi --help-query-gpu` in detail.
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

NUMBERS = ["device_num", "temperature", "total_memory", "available_memory", "used_memory", "gpu_volatile"]

def get_gpu_info(settings):
    """
        parsing nvidia-smi:
            version: 1 is for format of following
                +-----------------------------------------------------------------------------+
                | Processes:                                                       GPU Memory |
                |  GPU       PID  Type  Process name                               Usage      |
                |=============================================================================|
                |    0     16163    C   python                                         240MiB |
                |    1     16163    C   super_python                                  8522MiB |
                +-----------------------------------------------------------------------------+

                at least, around less version than 440.100 has this format

            version: 2 is for format of following
                +-----------------------------------------------------------------------------+
                | Processes:                                                                  |
                |  GPU   GI   CI        PID   Type   Process name                  GPU Memory |
                |        ID   ID                                                   Usage      |
                |=============================================================================|
                |    0   N/A  N/A     24898      C   nython                          17939MiB |
                |    1   N/A  N/A     24899      C   rython                          17063MiB |
                +-----------------------------------------------------------------------------+

                around more and eq than 450.51.06 has this format

            these version differences will effect the parsing using awk command 


        example output of this function
            {'gpu:0',
                  {'available_memory': '10934',
                   'device_num': '0',
                   'gpu_name': 'GeForce GTX 1080 Ti',
                   'gpu_volatile': '0',
                   'processes': [{'name': '/usr/bin/X',
                                  'pid': '1963',
                                  'used_memory': '148',
                                  'user': 'root'},
                                 {'name': 'compiz',
                                  'pid': '3437',
                                  'used_memory': '84',
                                  'user': 'user1'}],
                   'temperature': '36',
                   'timestamp': '2018/11/30 23:29:47.115',
                   'total_memory': '11169',
                   'used_memory': '235',
                   'uuid': 'GPU-...'}),
            {'gpu:1',
                  {'available_memory': '11170',
                   'device_num': '1',
                   'gpu_name': 'GeForce GTX 1080 Ti',
                   'gpu_volatile': '0',
                   'processes': [],
                   'temperature': '38',
                   'timestamp': '2018/11/30 23:29:47.117',
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
            `nvidia-smi | awk '$2=="Processes:" {p=1} p && $2 ~ /[0-9]+/ && $3 > 0 {print $2,$3,$5,$6}'`
            output of above command is like
                `0 30348 python 3679MiB`
            this way is easier, I think, but it really depends on the format of nvidia-smi.

        at this time, I chose 2.
    """

    gpu_info_dict = cl.OrderedDict()

    # get gpu status ######################################################################
    query_list = list(map(lambda x: x[0], GPU_QUERY))
    alias_list = list(map(lambda x: x[1], GPU_QUERY))

    # nounits means no % or MiB or so on
    cmd = '{} --query-gpu={} --format=csv,noheader,nounits'.format(settings.NVIDIA_SMI, ','.join(query_list))
    output = subprocess.check_output(cmd, shell=True).decode("utf-8")
    lines = output.split('\n')
    lines = [ line.strip() for line in lines if line.strip() != '' ]

    for line in lines:
        line = line.split(", ")
        gpu_info_dict["gpu:{}".format(line[0])] = {k:int(v) if k in NUMBERS else v for k, v in zip(alias_list+["processes"], line+[[]])}

    # get gpu processes ##################################################################
    if settings.NVIDIA_SMI_PARSE_VER == 1:
        """
        parse
        +-----------------------------------------------------------------------------+
        | Processes:                                                       GPU Memory |
        |  GPU       PID  Type  Process name                               Usage      |
        |=============================================================================|
        |    0     16163    C   python                                         240MiB |
        |    1     16163    C   super_python                                  8522MiB |
        +-----------------------------------------------------------------------------+
        """
        cmd = "nvidia-smi | awk '$2==\"Processes:\" {{p=1}} p && $2 ~ /[0-9]+/ && $3 > 0 {{print $2,$3,$5,$6}}'".format(settings.NVIDIA_SMI)
    elif settings.NVIDIA_SMI_PARSE_VER == 2:
        """
        parse
        +-----------------------------------------------------------------------------+
        | Processes:                                                                  |
        |  GPU   GI   CI        PID   Type   Process name                  GPU Memory |
        |        ID   ID                                                   Usage      |
        |=============================================================================|
        |    0   N/A  N/A     24898      C   nython                          17939MiB |
        |    1   N/A  N/A     24899      C   rython                          17063MiB |
        +-----------------------------------------------------------------------------+
        """
        cmd = "nvidia-smi | awk '$2==\"Processes:\" {{p=1}} p && $2 ~ /[0-9]+/ && $3 > 0 {{print $2,$5,$7,$8}}'".format(settings.NVIDIA_SMI)
    else:
        # this is same as NVIDIA_SMI_PARSE_VER == 1
        cmd = "nvidia-smi | awk '$2==\"Processes:\" {{p=1}} p && $2 ~ /[0-9]+/ && $3 > 0 {{print $2,$3,$5,$6}}'".format(settings.NVIDIA_SMI)

    output = subprocess.check_output(cmd, shell=True).decode("utf-8")
    lines = output.split('\n')
    lines = [ line.strip().split(" ") for line in lines if line.strip() != '' ]

    for line in lines:
        # each line will have ["gpu index", "pid", "command", "Used memory"]
        pid_user = subprocess.check_output('ps -o uname= -p "{}"'.format(line[1]), shell=True).decode("utf-8").strip("")
        gpu_info_dict["gpu:{}".format(line[0])]["processes"].append({"pid":line[1],
                                                                     "name":line[2],
                                                                     "user":pid_user.rstrip("\n"),
                                                                     "used_memory":int(line[3].replace("MiB", ""))})
    
    return gpu_info_dict

def register(settings, yaml_path):
    """
        register to server and get token.
    """

    host_name = os.uname()[1]

    resp = requests.get("http{}://{}:{}/register/?host_name={}&token={}".format("s" if settings.USE_HTTPS else "", 
                                                                                settings.IP, settings.PORT_NUM,
                                                                                host_name, settings.TOKEN))
    if resp.status_code == requests.codes.ok:
        resp_dict = resp.json()
        if resp_dict["status_code"] == 200:
            # it will returns like
            # {'id': 'f77818f42cabfdf1358250463a2db3d6', 'register_name': 'script_test', 'status': 'OK', 'status_code': 200}

            with open(yaml_path, "w") as yaml_writer:
                yaml_writer.write(yaml.dump({"hash_key":resp_dict["id"], "registered_name":resp_dict["register_name"]},
                                            default_flow_style=False))

            return resp_dict["id"]

def post_data(settings, token, yaml_path):
    content = get_gpu_info(settings)

    resp = requests.post("http{}://{}:{}/update/host/{}?token={}".format("s" if settings.USE_HTTPS else "",
                                                                         settings.IP, settings.PORT_NUM, token, settings.TOKEN),
                         data=json.dumps(content), headers={'Content-Type': 'application/json'})
    if resp.status_code == requests.codes.ok:
        resp_dict = resp.json()

        # in case server has initialized the database
        if resp_dict["status_code"] == 404:
            token = register(settings, yaml_path)
            resp = requests.post("http{}://{}:{}/update/host/{}?token={}".format("s" if settings.USE_HTTPS else "",
                                                                                 settings.IP, settings.PORT_NUM, token, settings.TOKEN),
                                 data=json.dumps(content), headers={'Content-Type': 'application/json'})

def send_info(settings):
    """
        settings
            settings must have following instance variable
                IP                                      :str
                PORT_NUM                                :int
                TOKEN                                   :str
                YAML_DIR                                :str
                YAML_NAME                               :str
                NVIDIA_SMI                              :str
                USE_HTTPS                               :bool

            typically, I recommend using `argparse`.
            see `gpu_info_sender.py` for more detail.
    """

    yaml_path = path_join(settings.YAML_DIR, settings.YAML_NAME+".yaml")

    # in case it does not exist
    mkdir(settings.YAML_DIR)

    if path_exist(yaml_path):
        with open(yaml_path, "r") as f:
            yaml_data = yaml.load(f, yaml.FullLoader)
            if yaml_data is not None:
                token = yaml_data["hash_key"]
            else:
                token = register(settings, yaml_path)
    else:
        token = register(settings, yaml_path)

    post_data(settings, token, yaml_path)
