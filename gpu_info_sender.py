import argparse

from vesta.send_gpu_info import send_info

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    # overwrite the settings
    parser.add_argument('--local_settings_path', type=str, default=None, help='yaml file path which overwrite the contents in vesta/settings.py')

    parser.add_argument('--yaml_dir', type=str, default="data", help='the dir of yaml which token is saved.')
    parser.add_argument('--yaml_name', type=str, default="token", help='path of yaml file.')
    parser.add_argument('--nvidia-smi', type=str, default="nvidia-smi", help='if you want to specify nvidia-smi command.')
    parser.add_argument('--use_https', action="store_true", default=False, help='')

    args = parser.parse_args()

    if args.local_settings_path is not None:
        try:
            with open(args.local_settings_path, "r") as yaml_file:
                yaml_data = yaml.load(yaml_file)

            for arg_key in yaml_data:
                if arg_key == "IP": settings.IP = yaml_data[arg_key]
                elif arg_key == "PORT_NUM": settings.PORT_NUM = int(yaml_data[arg_key])
                elif arg_key == "TOKEN": settings.TOKEN = yaml_data[arg_key]

        except Exception as e:
            print(e)
    
    send_info(args.yaml_name, args.yaml_dir, args.nvidia_smi, args.use_https)
