"""
    text formatting function
"""

def truncate_str(text, length=25, fill_char=None, ellipsis="…", align_right=False):
    """
        <------------- length ----------------->
                   fill_char
                    /
                   v
        text####################################

                                            ellipsis
                                               |
                                               v
        text_text_text_text_text_text_text_text…

        if align_right is true
        ####################################text
    """
    
    if len(text) > length:
        return text[:length-len(ellipsis)]+ellipsis
    elif fill_char is not None:
        if align_right:
            return "{}{}".format(fill_char*(length-len(text)), text)
        else:
            return "{}{}".format(text, fill_char*(length-len(text)))
    else:
        return text

def align_str(text, fill_char=" ", margin_char=" ", margin=(1,1), length=60, start=4, ellipsis="…", new_line=True):
    """
        <------------- length ----------------->
                   start   margin_char   fill_char
                    /       /             /
                   v       v             v
        #######    text      ###################
               <-->    <---->  
                  margin     
    """

    margin_start_pos = max(0, start-margin[0])

    # truncate text if it reached to length
    if len(text)+margin_start_pos >= length:
        text = text[margin_start_pos:length-len(ellipsis)-1]+ellipsis

    text_end_pos = (margin_start_pos+1)+len(text)
    suf_margin_len = min(margin[1], length-text_end_pos)

    arg = {
            "pre_fill_str"   : fill_char*(margin_start_pos),
            "pre_margin_str" : margin_char*margin[0],
            "text"           : text,
            "suf_margin_str" : margin_char*suf_margin_len,
            "suf_fill_str"   : fill_char*max(0, length-suf_margin_len-text_end_pos),
            "new_line"       : "\n" if new_line else ""
           }

    return "{pre_fill_str}{pre_margin_str}{text}{suf_margin_str}{suf_fill_str}{new_line}".format(**arg)

def create_bar_str(current, total, msg="", fill_char="/", empty_char=" ", left_bracket="[", right_bracket="]",
                   length=60, new_line=True):
    """
        <------------- length ----------------->
     left_bracket  fill_char   empty_char  right_bracket
           \        /            /         /
            v      v            v         v
        msg [///////////////              ]  50%
    """

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
        ├── /usr/bin/X                   148MiB
        └── compiz                        84MiB 
    """

    process_str = ""

    for index, process_data in enumerate(process_list):
        if index == len(process_list)-1:
            process_str += "{}{}{}{}".format(add_before, truncate_str("└── {} {:6d}MiB".format(
                                                                      truncate_str(process_data['name'], 
                                                                                   length=cmd_len,
                                                                                   fill_char=" ",
                                                                                   ellipsis="…"),
                                                                      int(process_data['used_memory'])),
                                                                      length=length,
                                                                      fill_char=" ",
                                                                      ellipsis="…"),
                            add_after,
                            "\n" if new_line else "")
        else:
            process_str += "{}{}{}{}".format(add_before, truncate_str("├── {} {:6d}MiB".format(
                                                                      truncate_str(process_data['name'], 
                                                                                   length=cmd_len,
                                                                                   fill_char=" ",
                                                                                   ellipsis="…"),
                                                                      int(process_data['used_memory'])),
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

    info =  "+------------------+------------------------+-----------------+--------+-------+\n"
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
            h = truncate_str(host_name, length=22, fill_char=" ", ellipsis="…", align_right=False)
            ip = truncate_str(host_info["ip_address"], length=15, fill_char=" ", ellipsis="…", align_right=True)
            ts = truncate_str(host_info["data"][0]["timestamp"], length=21, fill_char=" ", ellipsis="…", align_right=False)
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
                                   fill_char="#", margin_char=" ", margin=(1,1), length=term_width, start=4)
            info += align_str("last update: {}".format(data["timestamp"]),
                              fill_char="-", margin_char=" ", margin=(2,0), length=term_width, start=0)
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
              │  ├── /usr/bin/X                   148MiB                                   │  
              │  └── compiz                        84MiB                                   │  
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
            info += "\n"+align_str(host_name+" | {}".format(host_info["ip_address"]),
                                   fill_char="#", margin_char=" ", margin=(1,1), length=term_width, start=4)
            info += align_str("last update: {}".format(host_info["data"][0]["timestamp"]),
                              fill_char=" ", margin_char=" ", margin=(2,0), length=term_width, start=0)
            info += hr

            info += box_ul
            info += box_sp
            info += "  │  {}│\n".format(truncate_str("status: {}".format(host_info["status"]),
                                                   length=term_width-8, fill_char=" ", ellipsis="…", align_right=False))
            info += box_sp
            info += box_bl

        info += ul

    return info
