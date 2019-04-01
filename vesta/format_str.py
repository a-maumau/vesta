"""
    text formatting functions
"""

def truncate_str(text, length=25, fill_char=None, ellipsis="…", align_right=False, ellipsis_left=False):
    """
        <------------- length ----------------->
                   fill_char
                    /
                   v
        text####################################

        if align_right is true:
        ####################################text

                                            ellipsis
                                               |
                                               v
        text_text_text_text_text_text_text_text…

        if ellipsis_left is true:
        …ext_text_text_text_text_text_text_text_

    """

    if length <= 0:
        return ""
    
    if len(text) > length:
        if ellipsis_left:
          # it don't need -1 because it start from 0
            return ellipsis+text[len(text)-(length-len(ellipsis)):]
        else:
            return text[:length-len(ellipsis)]+ellipsis
    elif fill_char is not None:
        if align_right:
            return "{}{}".format(fill_char*(length-len(text)), text)
        else:
            return "{}{}".format(text, fill_char*(length-len(text)))
    else:
        return text

def align_str(text, fill_char=" ", margin_char=" ", start=4, margin=(0,0), length=60, ellipsis="…", new_line=True):
    """
    args:
        start: int
          set start point of magin or text.
          first char is 0

        <------------- length ----------------->
                 start    margin_char   fill_char
                /        /             /
               v        v             v
        #######    text      ###################
               <-->    <---->  
                  margin     
    """

    if length <= 0:
        return ""

    align_text = ""

    margin_start_pos = min(max(0, start), length)
    align_text += fill_char*margin_start_pos

    remaining_chars = length-margin_start_pos
    align_text += margin_char*min(margin[0], remaining_chars)

    # truncate text if it reached to length
    if len(text)+margin_start_pos > length:
        remaining_chars = length-len(align_text)
        align_text += text[0:remaining_chars-len(ellipsis)]+ellipsis
    else:
        align_text += text

    remaining_chars = length-len(align_text)

    remaining_chars -= margin[1]
    align_text += margin_char*max(min(margin[1] ,remaining_chars),0)

    align_text += fill_char*max(0, remaining_chars)

    text_end_pos = (margin_start_pos+1)+len(text) 
    suf_margin_len = min(margin[1], length-text_end_pos)

    if new_line:
        align_text += "\n"

    return align_text

def create_bar_str(current, total, msg="", fill_char="/", empty_char=" ", left_bracket="[", right_bracket="]",
                   length=60, new_line=True):
    """
        <------------- length ----------------->
    left_bracket  fill_char   empty_char  right_bracket
           \        /            /         /
            v      v            v         v
        msg [///////////////              ]  50%
         ^
         |
         msg
    """

    if length <= 0:
        return ""

    bar_len = length-len(left_bracket)-len(right_bracket)-len(" ddd%")-len(msg)
    fill_num = int((current/total)*bar_len)
    percent = int((current/total)*100)

    return "{} {}{}{}{} {:3d}%{}".format(
            msg, left_bracket, fill_char*fill_num, empty_char*(bar_len-fill_num), right_bracket,
            percent, "\n" if new_line else "")

def format_gpu_base_info_str(temperature, used_memory, total_memory, available_memory, gpu_volatile, length,
                             add_before="", add_after="", new_line=True):
    """
             memory used  memory available  gpu volatile  temperature
          235 / 11169MiB          10934MiB           10%         36°C
    """
    gpu_info_str = "{}{}{}{}".format(add_before,
                                     truncate_str("     memory used  memory available  gpu volatile  temperature",
                                                  length=length, fill_char=" ", ellipsis="…", align_right=False),
                                     add_after,
                                     "\n" if new_line else "")

    gpu_info_str += "{}{}{}{}".format(add_before,
                                      truncate_str("{:5d} / {:5d}MiB          {:5d}MiB          {:3d}%        {:3d}°C".format(
                                                   used_memory, total_memory, available_memory, gpu_volatile, temperature),
                                                   length=length, fill_char=" ", ellipsis="…", align_right=False),
                                      add_after,
                                      "\n" if new_line else "")

    return gpu_info_str

def format_process_str(process_list, length=80, cmd_len=25, add_before="", add_after="", new_line=True):
    """
        ├── /usr/bin/X                   148MiB user
        └── compiz                        84MiB user
    """

    if length <= 0:
        return ""

    process_str = ""

    for index, process_data in enumerate(process_list):
        if index == len(process_list)-1:
            process_str += "{}{}{}{}".format(add_before,
                                             truncate_str("└── {} {:5d}MiB {}".format(
                                                          truncate_str(process_data['name'], 
                                                                       length=cmd_len,
                                                                       fill_char=" ",
                                                                       ellipsis="…",
                                                                       ellipsis_left=True),
                                                          int(process_data['used_memory']),
                                                          process_data['user']),
                                                          length=length,
                                                          fill_char=" ",
                                                          ellipsis="…"),
                                             add_after,
                                             "\n" if new_line else "")
        else:
            process_str += "{}{}{}{}".format(add_before,
                                             truncate_str("├── {} {:5d}MiB {}".format(
                                                          truncate_str(process_data['name'], 
                                                                       length=cmd_len,
                                                                       fill_char=" ",
                                                                       ellipsis="…",
                                                                       ellipsis_left=True),
                                                          int(process_data['used_memory']),
                                                          process_data['user']),
                                                          length=length,
                                                          fill_char=" ",
                                                          ellipsis="…"),
                                             add_after,
                                             "\n" if new_line else "")

    return process_str

def format_gpu_info(fetch_data):
    """
        # width is now fix to 80
        +------------------+------------------------+-----------------+--------+-------+
        | host             | gpu                    | memory usage    | volat. | temp. |
        +------------------+------------------------+-----------------+--------+-------+
        |abcdefghijklmnopq…| 0:Geforce GTX 1080Ti   | 123456 / 123456 |   100 %| 100 °C|
        |                  | 1:Geforce GTX 1080Ti   | 123456 / 123456 |    89 %| 100 °C|
        |<-   18 chars   ->|<-      24 chars      ->|x<-  16 chars  ->| 7 chars| 6chars|
        +------------------+------------------------+-----------------+--------+-------+
        |                                                                              |
    """
    info  = "+------------------+------------------------+-----------------+--------+-------+\n"
    info += "| host             | gpu                    | memory usage    | volat. | temp. |\n"
    info += "+------------------+------------------------+-----------------+--------+-------+\n"

    _h = " "*18
    for host_name, host_info in fetch_data.items():
        if host_info["data"][0]["gpu_data"] != {}:
            data = host_info["data"][0]
            h = truncate_str(host_name, length=18, fill_char=" ", ellipsis="…", align_right=False)

            for i, (gpu, status) in enumerate(data["gpu_data"].items()):
                g = truncate_str("{:2d}:{}".format(status["device_num"], status["gpu_name"]),
                                 length=24, fill_char=" ", ellipsis="…", align_right=False)
                m = truncate_str("{:6d} / {:6d}".format(status["used_memory"], status["total_memory"]),
                                 length=16, fill_char=" ", ellipsis="…", align_right=False)
                v = truncate_str("{} %".format(status["gpu_volatile"]),
                                 length=7, fill_char=" ", ellipsis="…", align_right=True)
                t = truncate_str("{} °C".format(status["temperature"]),
                                 length=6, fill_char=" ", ellipsis="…", align_right=True)

                info += "|{}|{}| {}| {}| {}|\n".format(h if i == 0 else _h, g, m, v, t)

            info += "+------------------+------------------------+-----------------+--------+-------+\n"
        else:
            st = truncate_str(host_info["status"], length=69, fill_char=" ", ellipsis="…", align_right=False)

            # |   {host_name} ({host_ip}) last update: {}|
            # 1<3><- min24 ->11<-max15->11<-    33     ->1
            # it can use 38 char for host_name and host_ip
            h = truncate_str(host_name, length=38-len(host_info["ip_address"]), fill_char=" ", ellipsis="…", align_right=False)
            ip = truncate_str(host_info["ip_address"], length=len(host_info["ip_address"]), fill_char=" ", ellipsis="…", align_right=True)
            ts = truncate_str(host_info["data"][0]["timestamp"], length=20, fill_char=" ", ellipsis="…", align_right=False)
            info += "| status: {}|\n".format(st)
            info += "|   {} ({}) last update: {}|\n".format(h, ip, ts)
            info += "+------------------+------------------------+-----------------+--------+-------+\n"

    return info

def format_gpu_detail_info(fetched_data, term_width=80):
    info = ""
    hr = "-"*term_width+"\n"
    ul = "_"*term_width+"\n"
    
    box_ul = "  ┌"+"─"*(term_width-6)+"┐\n"
    box_bl = "  └"+"─"*(term_width-6)+"┘\n"
    box_sp = "  │"+" "*(term_width-6)+"│\n"

    for host_name, host_info in fetched_data.items():
        if host_info["data"][0]["gpu_data"] != {}:
            data = host_info["data"][0]

            info += "\n"+align_str(host_name+" :: {}".format(host_info["ip_address"]),
                                   fill_char="#", margin_char=" ", start=4, margin=(1,1), length=term_width)
            info += align_str("last update: {}".format(data["timestamp"]),
                              fill_char=" ", margin_char=" ", start=2, margin=(0,0), length=term_width)
            info += hr

            """ ┌　┐　┘　└ ─ │
                                              term width
            <-------------------------------------------------------------------------------->

            <>  <- margin 2chars                                          margin 2chars ->  <>
              ┌[ gpu:0 GeForce GTX 1080 Ti 2018/12/01 14:32:37.140 ]───────────────────────┐  
              │     memory used  memory available  gpu volatile  temperature               │  
              │  235 / 11169MiB          10934MiB            0%         36°C               │  
              │                                                                            │  
              │ mem [/                                                              ]   2% │  
              │  ├── /usr/bin/X                   148MiB user                              │  
              │  └── compiz                        84MiB user                              │  
              └────────────────────────────────────────────────────────────────────────────┘  
            """
            for gpu, status in data["gpu_data"].items():
                info += "  ┌{}┐\n".format(truncate_str("[ {} {} {} ]".format(gpu, status["gpu_name"], status["timestamp"]),
                                      length=term_width-6, fill_char="─", ellipsis="…", align_right=False))
                info += format_gpu_base_info_str(int(status['temperature']), int(status['used_memory']),
                                                 int(status['total_memory']), int(status['available_memory']),
                                                 int(status['gpu_volatile']), term_width-7,
                                                 add_before="  │ ", add_after="│")
                info += box_sp
                info += "  │ {} │\n".format(create_bar_str(current=int(status['used_memory']), total=int(status['total_memory']),
                                           msg="mem", length=term_width-9, new_line=False))
                info += format_process_str(status["processes"], length=term_width-9, cmd_len=25, add_before="  │  ", add_after=" │")
                info += box_bl
                info += "\n"

        else:
            info += "\n"+align_str(host_name+" :: {}".format(host_info["ip_address"]),
                                   fill_char="#", margin_char=" ", start=4, margin=(1,1), length=term_width)
            info += align_str("last update: {}".format(host_info["data"][0]["timestamp"]),
                              fill_char=" ", margin_char=" ", start=0, margin=(2,0), length=term_width)
            info += hr

            info += box_ul
            info += box_sp
            info += "  │  {}│\n".format(truncate_str("status: {}".format(host_info["status"]),
                                                   length=term_width-8, fill_char=" ", ellipsis="…", align_right=False))
            info += box_sp
            info += box_bl

        info += ul

    return info

def format_gpu_table(fetch_data):
    """
        # width is now fix to 80
        +------------------------------+---------------------------+-------------------+
        | host name                    | gpu name                  | memory usage (MiB)|
        +------------------------------+---------------------------+-------------------+
        |abcdefghijklmnopqrstuvwxyzabc…| 0:Geforce GTX 1080Ti      | 0123456 / 0123456 |
        |                              | 1:Geforce GTX 1080Ti      | 0123456 / 0123456 |
        |<-          30 chars        ->|<-      27 chars         ->|x<-   17 chars  ->x|    
        +------------------------------+---------------------------+-------------------+
        |                                                                              |
    """
    info  = "+------------------------------+---------------------------+-------------------+\n"
    info += "| host name                    | gpu name                  | memory usage (MiB)|\n"
    info += "+------------------------------+---------------------------+-------------------+\n"

    _h = " "*30
    for host_name, host_info in fetch_data.items():
        if host_info["data"][0]["gpu_data"] != {}:
            data = host_info["data"][0]
            h = truncate_str(host_name, length=30, fill_char=" ", ellipsis="…", align_right=False)

            for i, (gpu, status) in enumerate(data["gpu_data"].items()):
                g = truncate_str("{:2d}:{}".format(status["device_num"], status["gpu_name"]),
                                 length=27, fill_char=" ", ellipsis="…", align_right=False)
                m = truncate_str("{:7d} / {:7d}".format(status["used_memory"], status["total_memory"]),
                                 length=17, fill_char=" ", ellipsis="…", align_right=True)

                info += "|{}|{}| {} |\n".format(h if i == 0 else _h, g, m)

            info += "+------------------------------+---------------------------+-------------------+\n"
        else:
            st = truncate_str(host_info["status"], length=69, fill_char=" ", ellipsis="…", align_right=False)

            # |   {host_name} ({host_ip}) last update: {}|
            # 1<3><- min24 ->11<-max15->11<-    33     ->1
            # it can use 38 char for host_name and host_ip
            h = truncate_str(host_name, length=38-len(host_info["ip_address"]), fill_char=" ", ellipsis="…", align_right=False)
            ip = truncate_str(host_info["ip_address"], length=len(host_info["ip_address"]), fill_char=" ", ellipsis="…", align_right=True)
            ts = truncate_str(host_info["data"][0]["timestamp"], length=20, fill_char=" ", ellipsis="…", align_right=False)
            info += "| status: {}|\n".format(st)
            info += "|   {} ({}) last update: {}|\n".format(h, ip, ts)
            info += "+------------------------------+---------------------------+-------------------+\n"

    return info

