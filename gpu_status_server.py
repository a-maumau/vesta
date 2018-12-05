import ssl
import argparse

from vesta.server import HTTPServer

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

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
    parser.add_argument('--down_th', type=int, default=300, help='in sec.')

    parser.add_argument('-quiet', action="store_true", default=False, help='only showing the log of loss and validation.')

    args = parser.parse_args()

    ssl_context = None
    if args.ssl_cert is not None:
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        ssl_context.load_cert_chain(args.ssl_cert, args.ssl_key)

    server = HTTPServer(database_name=args.db_name, database_dir=args.db_dir, name=args.server_name,
                        bind_host=args.bind_host, term_width=args.term_width, quiet=args.quiet)
    server.start(ssl_context=ssl_context)
    server.watch_and_sleep(args.sleep_time, args.down_th)
