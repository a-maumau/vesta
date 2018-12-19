import argparse

from vesta.send_gpu_info import send_info

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('--yaml_dir', type=str, default="data", help='the dir of yaml which token is saved.')
    parser.add_argument('--yaml_name', type=str, default="token", help='path of yaml file.')
    parser.add_argument('--nvidia-smi', type=str, default="nvidia-smi", help='if you want to specify nvidia-smi command.')
    parser.add_argument('--use_https', action="store_true", default=False, help='')

    args = parser.parse_args()
    
    send_info(args.yaml_name, args.yaml_dir, args.nvidia_smi, args.use_https)
