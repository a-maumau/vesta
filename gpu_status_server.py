import ssl
import yaml
import argparse

from vesta import settings
from vesta.server import HTTPServer

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    # overwrite the settings
    parser.add_argument('--local_settings_path', type=str, default=None, help='yaml file path which overwrite the contents in vesta/settings.py')

    # args for server
    parser.add_argument('--db_name', type=str, default="gpu_states.db", help='database name.')
    parser.add_argument('--db_dir', type=str, default="data", help='dir of database.')
    parser.add_argument('--server_name', type=str, default="gpu_monitor", help='')
    parser.add_argument('--bind_host', type=str, default="0.0.0.0", help='bind host IP address.')
    # for bind post, please change PORT_NUM in settings.

    # ssl settings certfile, keyfile=None, password
    parser.add_argument('--ssl_cert', type=str, default=None, help='')
    parser.add_argument('--ssl_key', type=str, default=None, help='')

    parser.add_argument('--term_width', type=int, default=80, help='width of terminal printing.')

    # args for waching part
    parser.add_argument('--sleep_time', type=int, default=5, help='in sec.')
    parser.add_argument('--down_th', type=int, default=60, help='in sec.')

    parser.add_argument('-quiet', action="store_true", default=False, help='only showing the log of loss and validation.')

    args = parser.parse_args()

    ssl_context = None
    if args.ssl_cert is not None:
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        ssl_context.load_cert_chain(args.ssl_cert, args.ssl_key)

    if args.local_settings_path is not None:
        try:
            with open(args.local_settings_path, "r") as yaml_file:
                yaml_data = yaml.load(yaml_file)

            for arg_key in yaml_data:
                if arg_key == "IP": settings.IP = yaml_data[arg_key]
                elif arg_key == "PORT_NUM": settings.PORT_NUM = int(yaml_data[arg_key])
                elif arg_key == "TOKEN": settings.TOKEN = yaml_data[arg_key]
                elif arg_key == "PAGE_PER_HOST_NUM": settings.PAGE_PER_HOST_NUM = int(yaml_data[arg_key])
                elif arg_key == "PAGE_TITLE": settings.PAGE_TITLE = yaml_data[arg_key]
                elif arg_key == "PAGE_DESCRIPTION": settings.PAGE_DESCRIPTION = yaml_data[arg_key]
                elif arg_key == "SLACK_WEBHOOK": settings.SLACK_WEBHOOK = yaml_data[arg_key]
                elif arg_key == "SLACK_BOT_TOKEN": settings.SLACK_BOT_TOKEN = yaml_data[arg_key]
                elif arg_key == "SLACK_BOT_POST_CHANNEL": settings.SLACK_BOT_POST_CHANNEL = yaml_data[arg_key]
                elif arg_key == "VALID_NETWORK": settings.VALID_NETWORK = yaml_data[arg_key]
                elif arg_key == "SCHEDULE_FUNCTION": settings.SCHEDULE_FUNCTION = yaml_data[arg_key]
                elif arg_key == "REGISTER_UPLINK_MSG": settings.REGISTER_UPLINK_MSG = yaml_data[arg_key]
                elif arg_key == "UPDATE_UPLINK_MSG": settings.UPDATE_UPLINK_MSG = yaml_data[arg_key]
                elif arg_key == "HOST_DOWN_MSG": settings.HOST_DOWN_MSG = yaml_data[arg_key]
                elif arg_key == "KEYWORD_CMD_PREFIX": settings.KEYWORD_CMD_PREFIX = yaml_data[arg_key]
                elif arg_key == "KEYWORD_PRINT_HOSTS": settings.KEYWORD_PRINT_HOSTS = yaml_data[arg_key]
                elif arg_key == "KEYWORD_PRINT_ALL_HOSTS": settings.KEYWORD_PRINT_ALL_HOSTS = yaml_data[arg_key]
                elif arg_key == "KEYWORD_PRINT_ALL_HOSTS_CMD": settings.KEYWORD_PRINT_ALL_HOSTS_CMD = yaml_data[arg_key]
                elif arg_key == "KEYWORD_PRINT_ALL_HOSTS_DETAIL": settings.KEYWORD_PRINT_ALL_HOSTS_DETAIL = yaml_data[arg_key]
                elif arg_key == "KEYWORD_PRINT_HELP": settings.KEYWORD_PRINT_HELP = yaml_data[arg_key]

        except Exception as e:
            print(e)

    server = HTTPServer(database_name=args.db_name, database_dir=args.db_dir, name=args.server_name,
                        bind_host=args.bind_host, term_width=args.term_width, quiet=args.quiet)
    server.start(ssl_context=ssl_context)
    server.watch_and_sleep(args.sleep_time, args.down_th)
