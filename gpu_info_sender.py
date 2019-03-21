import argparse

from vesta.send_gpu_info import send_info

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('--local_settings_yaml_path', type=str, default=None,
                        help='yaml file path which overwrite the contents in vesta/settings.py')

    parser.add_argument('--ip', dest='IP', type=str, default="127.0.0.1",
                        help='this ip address is the server address for the client which send the gpu information.\nit is mainly for a machine which is sending the data to server.')
    parser.add_argument('--port_num', dest='PORT_NUM', type=int, default=8080, help="server's open port.")
    parser.add_argument('--token', dest='TOKEN', type=str, default="0000",
                        help="url parameter token for posting data.\nwhatever you want, actually it's doing nothing now. it is only for preventing accidental posting.")

    parser.add_argument('--yaml_dir', dest='YAML_DIR', type=str, default="data", help='the dir of yaml which token is saved.')
    parser.add_argument('--yaml_name', dest='YAML_NAME', type=str, default="token", help='path of yaml file.')
    parser.add_argument('--nvidia-smi', dest='NVIDIA_SMI', type=str, default="nvidia-smi", help='if you want to specify nvidia-smi command.')
    parser.add_argument('--use_https', dest='USE_HTTPS', action="store_true", default=False, help='')

    settings = parser.parse_args()

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
    
    send_info(settings)
