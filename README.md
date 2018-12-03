# Requirements
This script is depending on `Python3`, and `nvidia-smi`, `awk`, `ps` commands.  

# Setup
```
pip install -r requirements.txt
```  
If there is a missing package, please install by yourself using pip.  
also you need setup settings.py for your environment.   

# Usage
for Server  
```
python gpu_status_server.py
```  
  
for Nodes
```
python gpu_info_sender.py
```  
   
For automatical process, using systemd and crontab will do the works.  

## from Terminal
To get GPU information from terminal app, use curl and access `http://<server_address>/?term=true`.  
You will get like  
```
$ curl "http://0.0.0.0:8080/?term=true"
+------------------+------------------------+-----------------+--------+-------+
| host             | gpu                    | memory usage    | volat. | temp. |
+------------------+------------------------+-----------------+--------+-------+
|host1             | 0:GeForce GTX 1080 Ti  |    235 /  11169 |     0 %|  36 °C|
|                  | 1:GeForce GTX 1080 Ti  |      2 /  11172 |     0 %|  38 °C|
+------------------+------------------------+-----------------+--------+-------+
```

If you want to see detail information you can use `detail` option like `http://<server_address>/?term=true&detail=true`.  
You will get like  
```
$ curl "http://0.0.0.0:8080/?term=true&detail=true"

### host1 :: 127.0.0.1 #########################################################
  last update: 2018/12/03 23:16:59
--------------------------------------------------------------------------------
  ┌[ gpu:0 GeForce GTX 1080 Ti 2018/12/01 14:32:37.140 ]─────────────────────┐
  │      memory used  memory available  gpu volatile  temperature            │
  │   235 / 11169MiB          10934MiB            0%         36°C            │
  │                                                                          │
  │ mem [/                                                            ]   2% │
  │  ├── /usr/bin/X                   148MiB                                 │
  │  └── compiz                        84MiB                                 │
  └──────────────────────────────────────────────────────────────────────────┘

  ┌[ gpu:1 GeForce GTX 1080 Ti 2018/12/01 14:32:37.141 ]─────────────────────┐
  │      memory used  memory available  gpu volatile  temperature            │
  │     2 / 11172MiB          11170MiB            0%         38°C            │
  │                                                                          │
  │ mem [                                                             ]   0% │
  │  └── /usr/bin/X                   148MiB                                 │
  └──────────────────────────────────────────────────────────────────────────┘

________________________________________________________________________________

```
  
Server will also provide you to access host data by json.
Access `http://<server_address>/states/<host_name>/`, or to specify host `http://<server_address>/states/<host_name>/`  
You can use url parameter to fetch how many log you want by `fetch_num=<# you want>`  

## from Web Browser
Just access `http://<server_address>/`  
You will get like  
![sample web broser image](imgs/browser_sample_resized.png "sample")
  
# Response
User can get the information of GPU by accessing `http://<server_address>/states/`.  
Json response is like
```
{
    "host1":{
        # the order of data is ascending order in time
        "data":
            # host_name log are in array
            [ 
                {   # each GPU will be denote by "gpu:<device_num>"
                    'gpu_data':{
                        'gpu:0':{'available_memory': '10934',
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
                               .
                               .
                               .

                        }
                    },
                    "timestamp": 20181130232947 # server recorded timestamp YYYYMMDDhhmmss
                }
            ],
        "ip_address": 127.0.0.1 # host IP address
    },
    "host2":{...}
}
```

# Topology
Topology is very simple, Master (server) and Slave (each local machine) style, but it is ad hoc.  
Server is only waiting the slaves to post the gpu information.  

# Database
## machine table
`mchine` table is a lookup table for hash_code (id) to host name.  
Table field is

| id (TEXT) | name (TEXT)| ip_address (TEXT)|
|-----------|------------|------------|
| hash_code_1 | host_1 | host_1_ip |
| hash_code_2 | host_2 | host_2_ip |
| ... | ... | ... |
| hash_code_n | host_n | host_n_ip |
  
hash_code will be generated by Python code  
```
hash_code = random.getrandbits(128)
```
  
## {host} table
Each host has own table for logging.  
Table field is  

| timestamp (TEXT) | data (BLOB)|
|-----------|------------| 
| timestamp_1 | data_1 |
| timestamp_2 | data_2 |
| ... | ... |
| timestamp_n | data_n |
  
`timestamp` is based on server time zone and the style is "YYYYMMDDhhmmss".  
`data` is a Python dict object while it is serialized and compressed by Python bz2.  
