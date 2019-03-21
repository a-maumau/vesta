import ssl
import yaml
import argparse

from vesta.server import HTTPServer

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Easy running script for GPU monitor server.",
                                     epilog="")

    # overwrite the settings
    parser.add_argument('--local_settings_yaml_path', type=str, default=None,
                        help='yaml file path which overwrite the contents args.')

    # args for server
    parser.add_argument('--db_name', dest='DB_NAME', type=str, default="gpu_states.db", help='database name.')
    parser.add_argument('--db_dir', dest='DB_DIR', type=str, default="data", help='dir of database.')
    parser.add_argument('--server_name', dest='SERVER_NAME', type=str, default="gpu_monitor", help='')
    parser.add_argument('--bind_host', dest='BIND_HOST', type=str, default="0.0.0.0",
                        help='bind host IP address.\nthis should be 0.0.0.0.\nif you want to filter IP addresses, use `--valid_network`.')

    # ssl settings certfile, keyfile=None, password
    parser.add_argument('--ssl_cert', dest='SSL_CERT', type=str, default=None, help='path of ssl certificate file.')
    parser.add_argument('--ssl_key', dest='SSL_KEY', type=str, default=None, help='path for ssl key file.')

    parser.add_argument('--term_width', dest='TERM_WIDTH', type=int, default=80, help='width of terminal printing.')

    # args for waching part
    parser.add_argument('--server_sleep_time', dest='SERVER_SLEEP_TIME', type=int, default=5, help='server sleeping time in sec.')
    parser.add_argument('--down_th', dest='DOWN_TH', type=int, default=60,
                        help='threshold of deciding machines are down in sec.\nif your monitoring machine is sending information in interval that is more than this value, it will always decide it is down. so at least you need to set this value more than that.')

    parser.add_argument('--ws_receive_timeout', dest='WS_RECEIVE_TIMEOUT', type=int, default=1, help='server waiting time of websocket request in sec.')
    parser.add_argument('--slack_bot_sleep_time', dest='SLACK_BOT_SLEEP_TIME', type=int, default=1, help="slack bot's waiting time (response time) in sec.")
    parser.add_argument('--save_interval', dest='SAVE_INTERVAL', type=int, default=60,
                        help='at least interval time for saving data in sec.\nthis is for controlling the data which is will save in database. if you want to save all data, set this to 0.')

    parser.add_argument('--sort_by', dest='SORT_BY', type=str, default="ip", choices=['ip', 'name'],
                        help='sort type of machine arrangement. choice from `ip` or `name`.')

    parser.add_argument('--ip', dest='IP', type=str, default="127.0.0.1",
                        help='this ip address is the server address for the client which send the gpu information.\nit is mainly for a machine which is sending the data to server.')
    parser.add_argument('--port_num', dest='PORT_NUM', type=int, default=8080, help="server's open port.")
    parser.add_argument('--token', dest='TOKEN', type=str, default="0000",
                        help="url parameter token for posting data.\nwhatever you want, actually it's doing nothing now. it is only for preventing accidental posting.")

    parser.add_argument('--page_per_host_num', dest='PAGE_PER_HOST_NUM', type=int, default=8,
                        help='how many information to read in each page.\nit is controlling the view of html page.')
    parser.add_argument('--page_title', dest='PAGE_TITLE', type=str, default="GPUs", help='page title of html page.')
    parser.add_argument('--page_description', dest='PAGE_DESCRIPTION', type=str, default="", help='page description of html page.')
    
    parser.add_argument('--slack_webhook', dest='SLACK_WEBHOOK', type=str, default="",
                        help='for slack notification. set a webhook url.\nit will send a up/down notification to this webhook.')
    parser.add_argument('--slack_bot_token', dest='SLACK_BOT_TOKEN', type=str, default="",
                        help='for data access from slack. set slack bot token.\nif you use slack bot, slack bot can post gpu statuses.')
    parser.add_argument('--slack_bot_post_channel', dest='SLACK_BOT_POST_CHANNEL', type=str, default="", help="channel for where to post. it is used in 'vesta::server::send_hosts_statuses()'.")

    parser.add_argument('--valid_network', dest='VALID_NETWORK', type=str, default="127.0.0.1",
                        help='to filter valid IP address.\nit will be used in `re.search()`, so you can use regular expressions.')

    # must be a iteratable object
    parser.add_argument('--shedule_function', dest='SCHEDULE_FUNCTION', type=str, nargs='*', default=[],
                        help="if you want send shceduled status report, use this function.\nyou can use python schedule module to schedule the announcement of something like `'schedule.every().day.at('00:00').do(self.send_hosts_statuses, 'SCHEDULED_STATUS_REPORT')'`. this will go through `exec()` be careful.")

    # notification message ########################################
    parser.add_argument('--register_uplink_msg', dest='REGISTER_UPLINK_MSG', type=str, default="⬆︎⬆︎⬆︎ `Uplink` Detected - New uplink from `{}`. Hello!",
                        help='notification message of new host came.\nif you use {} it will be filled with `host name`')
    parser.add_argument('--re_uplink_msg', dest='RE_UPLINK_MSG', type=str, default="⬆︎⬆︎⬆︎ `  Up  ` Detected - Uplink from `{}`. Welcome back!",
                        help='notification message of host has come up from down status or waiting status.\nif you use {} it will be filled with `host name`.')
    parser.add_argument('--host_down_msg', dest='HOST_DOWN_MSG', type=str, default="⬇︎⬇︎⬇︎ ` Down ` Detected - Connection from `{}` has been lost more than {} sec. Check network and machine.",
                        help='notification message of server decided host is down.\nif you use {}, you have to use two {} and it will be filled with `host name` and `at least lost connection interval sec`.')

    parser.add_argument('--keyword_cmd_prefix', dest='KEYWORD_CMD_PREFIX', type=str, default="",
                        help="slack bot's command prefix\nset prefix if you want to discriminate commands and usual word.")
    # show all host names
    parser.add_argument('--keyword_print_hosts', dest='KEYWORD_PRINT_HOSTS', type=str, default="HOSTS", help='if you set to "" i will be disabled')
    # same result as server::send_hosts_statuses()
    parser.add_argument('--keyword_print_all_hosts', dest='KEYWORD_PRINT_ALL_HOSTS', type=str, default="ALL", help='if you set to "" i will be disabled')
    # same result as command line using ?term=true
    parser.add_argument('--keyword_print_all_hosts_cmd', dest='KEYWORD_PRINT_ALL_HOSTS_CMD', type=str, default="ALL_cmd", help='if you set to "" i will be disabled')
    # same result as command line using ?term=true
    parser.add_argument('--keyword_print_all_hosts_detail', dest='KEYWORD_PRINT_ALL_HOSTS_DETAIL', type=str, default="ALL_detail", help='if you set to "" i will be disabled')
    # for help message
    parser.add_argument('--keyword_print_help', dest='KEYWORD_PRINT_HELP', type=str, default="HELP", help='if you set to "" i will be disabled')

    parser.add_argument('-quiet', dest='QUIET', action="store_true", default=False, help='show only critical error message.')

    settings = parser.parse_args()

    ssl_context = None
    if settings.SSL_CERT is not None:
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        ssl_context.load_cert_chain(settings.SSL_CERT, settings.SSL_KEY)

    if settings.local_settings_yaml_path is not None:
        try:
            with open(settings.local_settings_yaml_path, "r") as yaml_file:
                yaml_data = yaml.load(yaml_file)
        except Exception as e:
            print(e)
            yaml_data = []

        for arg_key in yaml_data:
            if arg_key in settings:
                setattr(settings, arg_key, yaml_data[arg_key])

    print(settings.SCHEDULE_FUNCTION)

    server = HTTPServer(settings)
    server.start(ssl_context=ssl_context)
    server.watch_and_sleep()
