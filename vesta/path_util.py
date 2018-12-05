import os 

def mkdir(folder_path):
    if not os.path.exists(os.path.expanduser(folder_path)):
        os.makedirs(os.path.expanduser(folder_path))

def isdir(folder_path):
    return os.path.isdir(os.path.expanduser(folder_path))

def path_exist(path):
    return os.path.exists(os.path.expanduser(path))

def path_join(*paths):
    return os.path.expanduser(os.path.join(*paths))
