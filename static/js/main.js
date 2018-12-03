/* Logics

    initialize
        when the base htmls are fetch from server,
            all contents will set to set_collapsible() ,and
            all charts in contents will init by init_chart).
        then it will establish websocket for fetch update.
        initial values of
            `page_data`, `page_all_num`, `now_page_num`, `ok_statuses`, `ws_url`
        are feed in index.html by server using jinja2.

    update
        if a new data comes from server it will update charts and some content.
        if the data was a new host it will append a new content

    page transition
        if the bottom paginator is clicked, the update list of host will
        change at server, which client has been sent which page that client want.
        according this new list of host, it will update the page.

    initial
        
       |     +--------+
       v     v        |
                      |
    page content -> update
       
       |              ^
       v              |
                      |
    transition -------*

*/

// for websocket
var ws;
// keep charts for update
var charts = {};

// avoiding many time declaration
var _mem_gauge;
var _vol_gauge;
var _temp_gauge;
var _mem_pie;
var _max_mem;
var _min_mem;
var _max_vol;
var _min_vol;
var _max_temp;
var _min_temp;
var _element_data;

function set_collapsible(host_name){
    coll = $("#"+host_name)[0]
    coll.addEventListener("click", function() {
        this.classList.toggle("active");
        var content = $("#"+host_name).find(".content")[0];
        if (content.style.maxHeight){
            content.style.maxHeight = null;
        }else{
        content.style.maxHeight = content.scrollHeight + "px";
        }
    })
}

function init_pagination(){
    if(now_page_num > 1){
        $(".pagination").find(".page-link.page_prev").addClass("has_link");
    }

    if(now_page_num < page_all_num){
        $(".pagination").find(".page-link.page_next").addClass("has_link");
    }

    $(".pagination").find(".page-link.this_page").text(now_page_num);
}

function page_transition(trans_num){
    var new_page_num = now_page_num+trans_num;

    if(new_page_num <= 1){
        new_page_num = 1;
        $(".pagination").find(".page-link.this_page").text(new_page_num);
        $(".pagination").find(".page-link.page_prev").removeClass("has_link");
        if(new_page_num < page_all_num){
            $(".pagination").find(".page-link.page_next").addClass("has_link");    
        }
    }else if(new_page_num >= page_all_num){
        new_page_num = page_all_num;
        $(".pagination").find(".page-link.this_page").text(new_page_num);
        $(".pagination").find(".page-link.page_next").removeClass("has_link");
        if(new_page_num > 1){
            $(".pagination").find(".page-link.page_prev").addClass("has_link");    
        }
    }else{
        $(".pagination").find(".page-link.this_page").text(new_page_num);
        $(".pagination").find(".page-link.page_prev").addClass("has_link");
        $(".pagination").find(".page-link.page_next").addClass("has_link");
    }

    if(new_page_num != now_page_num){
        ws.send(new_page_num);
        now_page_num = new_page_num;
    }
}

function create_chart_data(data){
    var return_data = {gpu_process:{}}
    var count = 0
    var max_mem = 0;
    var min_mem = 0;
    var max_vol = 0;
    var min_vol = 0;
    var max_temp = 0;
    var min_temp = 0;

    for(var gpu_id in data){
        var proc_dict = {};
        var pie_chart_data = [];

        if(count == 0){
            max_mem = data[gpu_id]["used_memory"]/data[gpu_id]["total_memory"];
            min_mem = data[gpu_id]["used_memory"]/data[gpu_id]["total_memory"];
            max_vol = data[gpu_id]["gpu_volatile"];
            min_vol = data[gpu_id]["gpu_volatile"];
            max_temp = data[gpu_id]["temperature"];
            min_temp = data[gpu_id]["temperature"];
        }else{
            _max_mem = data[gpu_id]["used_memory"]/data[gpu_id]["total_memory"];
            _min_mem = data[gpu_id]["used_memory"]/data[gpu_id]["total_memory"];
            _max_vol = data[gpu_id]["gpu_volatile"];
            _min_vol = data[gpu_id]["gpu_volatile"];
            _max_temp = data[gpu_id]["temperature"];
            _min_temp = data[gpu_id]["temperature"];

            if(max_mem < _max_mem) max_mem = _max_mem;
            if(min_mem > _min_mem) min_mem = _min_mem;
            if(max_vol < _max_vol) max_vol = _max_vol;
            if(min_vol > _min_vol) min_vol = _min_vol;
            if(max_temp < _max_temp) max_temp = _max_temp;
            if(min_temp > _min_temp) min_temp = _min_temp;
        }

        for(var proc_index in data[gpu_id]["processes"]){
            proc_dict[data[gpu_id]["processes"][proc_index]["pid"]] = {
                name:data[gpu_id]["processes"][proc_index]["name"],
                user:data[gpu_id]["processes"][proc_index]["user"],
                used_memory:data[gpu_id]["processes"][proc_index]["used_memory"]
            };
            pie_chart_data.push({name: data[gpu_id]["processes"][proc_index]["name"],
                                 y: data[gpu_id]["processes"][proc_index]["used_memory"],
                                 id:data[gpu_id]["processes"][proc_index]["pid"]});
        }
        pie_chart_data.push({
                            name: 'Available',
                            y: data[gpu_id]["available_memory"],
                            dataLabels: {
                                enabled: false
                            },
                            color: "#888888"
                        });

        return_data["gpu_process"][gpu_id] = {processes:proc_dict, chart_data:pie_chart_data};
        count++;
    }

    return_data["max_mem"] = max_mem*100;
    return_data["min_mem"] = min_mem*100;
    return_data["max_volatile"] = max_vol;
    return_data["min_volatile"] = min_vol;
    return_data["max_temperature"] = max_temp;
    return_data["min_temperature"] = min_temp;

    return return_data;
}

function init_chart(host_name, data){
    var chart_data = create_chart_data(data["data"][0]["gpu_data"]);

    _mem_gauge = create_mem_usage_gauge(host_name+"_mem_gauge", parseFloat(chart_data["max_mem"].toFixed(1)), parseFloat(chart_data["min_mem"].toFixed(1)));
    _vol_gauge = create_volatile_gauge(host_name+"_vol_gauge", chart_data["max_volatile"], chart_data["min_volatile"]);
    _temp_gauge = create_temperature_gauge(host_name+"_temp_gauge", chart_data["max_temperature"], chart_data["min_temperature"]);
    
    if(ok_statuses.indexOf(data["status"]) >= 0){
        _mem_pie = [];
        for(var gpu_id in chart_data["gpu_process"]){
            _mem_pie.push(create_mem_usage_detail_pie(host_name+"_"+gpu_id+"_mem_pie",
                chart_data["gpu_process"][gpu_id]["chart_data"],
                data["data"][0]["gpu_data"][gpu_id]["used_memory"],
                data["data"][0]["gpu_data"][gpu_id]["total_memory"]));
        }
        charts[host_name] = {mem_gauge:_mem_gauge, vol_gauge:_vol_gauge, temp_gauge:_temp_gauge, mem_pie:_mem_pie};
    }
}

function update_contents(host_name, data){
    /*
        not thinking the hosts gpu name and number will change.
    */

    var mem_gauge;
    var vol_gauge;
    var temp_gauge;
    var mem_pie;

    var chart_data = create_chart_data(data["data"][0]["gpu_data"]);

    var host_content_element = $("#"+host_name)

    host_content_element.find(".timestamp").text("last update: "+data["data"][0]["timestamp"]);

    // update charts
    charts[host_name]["mem_gauge"].series[0].data[0].update({y:parseFloat(chart_data["max_mem"].toFixed(1))});
    charts[host_name]["mem_gauge"].series[1].data[0].update({y:parseFloat(chart_data["min_mem"].toFixed(1))});
    charts[host_name]["vol_gauge"].series[0].data[0].update({y:parseFloat(chart_data["max_volatile"].toFixed(1))});
    charts[host_name]["vol_gauge"].series[1].data[0].update({y:parseFloat(chart_data["min_volatile"].toFixed(1))});
    charts[host_name]["temp_gauge"].series[0].data[0].update({y:parseFloat(chart_data["max_temperature"].toFixed(1))});
    charts[host_name]["temp_gauge"].series[0].data[1].update({y:parseFloat(chart_data["min_temperature"].toFixed(1))});

    var gpu_index = 0;
    var proces_content;
    var element;
    for(var gpu_id in chart_data["gpu_process"]){
        // it seems ":" is a token for filtering in jQuery.
        host_content_element.find("#"+host_name+"_gpu\\:"+String(gpu_index)+"_gpu_info").replaceWith('<tr id="'+host_name+'_'+gpu_id+'_gpu_info"><td class="tc_gpu_name">'+gpu_id+'</td><td class="tc_free_mem value">'+String(data["data"][0]["gpu_data"][gpu_id]["available_memory"])+'MiB</td><td class="tc_volatile value">'+String(data["data"][0]["gpu_data"][gpu_id]["gpu_volatile"])+'%</td><td class="tc_temperature value">'+String(data["data"][0]["gpu_data"][gpu_id]["temperature"])+'°C</td></tr>');
        host_content_element.find("#"+host_name+"_gpu\\:"+String(gpu_index)+"_entry").find(".gpu_info_text").text("available "+String(data["data"][0]["gpu_data"][gpu_id]["available_memory"])+" MiB, volatile "+String(data["data"][0]["gpu_data"][gpu_id]["gpu_volatile"])+"%, temperature "+String(data["data"][0]["gpu_data"][gpu_id]["temperature"])+"°C");

        // update memory usage pie chart
        charts[host_name]["mem_pie"][gpu_index].setTitle({text:'Memory<br>Usage<br><p style="color: #000">'+String(data["data"][0]["gpu_data"][gpu_id]["used_memory"])+'/'+String(data["data"][0]["gpu_data"][gpu_id]["total_memory"])+'</p><br>MiB'});
        charts[host_name]["mem_pie"][gpu_index].series[0].setData(chart_data["gpu_process"][gpu_id]["chart_data"], true);

        // add process table replacement code
        //if($('#.hoge').length){
            // if exits, here will be exec.
        //}
        proces_content = host_content_element.find("#"+host_name+"_gpu\\:"+String(gpu_index)+"_processes");
        
        element = '<tbody id="'+host_name+'_gpu:'+gpu_index+'_processes">';
        for(var pid in chart_data["gpu_process"][gpu_id]["processes"]){
            element += '<tr id="'+host_name+'_pid_'+pid+'"><td class="tc_command_name">'+chart_data["gpu_process"][gpu_id]["processes"][pid]["name"]+'</td><td class="tc_user_name">'+chart_data["gpu_process"][gpu_id]["processes"][pid]["user"]+'</td><td class="tc_used_memory value">'+String(chart_data["gpu_process"][gpu_id]["processes"][pid]["used_memory"])+'MiB</td></tr>';
        }

        proces_content.replaceWith(element);

        /*
        for animation, I wanted to delete non existing id and append new id
        but, I'm lazy, i just replace it all...
        proces_content.each(function(){ 
            console.log($(this).attr("id"))
        });
        */

        gpu_index++;
    }

}

function update(update_data){
    page_all_num = update_data["total_page_num"]

    var host_entry_head = $("#main_content");
    var insert_head = host_entry_head.find("#content_title");
    var page_content_name_list = Object.keys(page_data);
    var page_content_del_list = page_content_name_list.concat();
    var del_index;
    var host_name;

    for(var name_index in update_data["page_name_list"]){
        host_name = update_data["page_name_list"][name_index]

        // when new entry has come.
        if(page_content_name_list.indexOf(host_name) < 0){
            _element_data = fetch_content_element(host_name);
            if(_element_data["found"]){
                insert_head.after(_element_data["element"]);
                set_collapsible(host_name);
                init_chart(host_name, update_data["update"][host_name]);
                insert_head = host_entry_head.find("#"+host_name+"_hr");
                page_content_del_list = page_content_del_list.filter(function(x){return x !=host_name});
            }else{
                continue;
            }
        // check for update
        }else{
            // if update exist, then update it.
            if(host_name in update_data["update"]){
                if(update_data["update"][host_name]["status"] != page_data[host_name]["status"]){
                    _element_data = fetch_content_element(host_name);
                    $("#"+host_name).replaceWith(_element_data["element"]);
                    set_collapsible(host_name);
                    init_chart(host_name, update_data["update"][host_name]);
                }else{
                    update_contents(host_name, update_data["update"][host_name]);
                }
            }
            // delete from deleteing content list
            page_content_del_list = page_content_del_list.filter(function(x){return x !=host_name});
            // move to next index
            insert_head = host_entry_head.find("#"+host_name+"_hr");
        }

        // replace with updated data
        page_data[host_name] = update_data["update"][host_name];
    }

    // delete contents which are not anymore in the page content list
    for(var index in page_content_del_list){
        $("#"+page_content_del_list[index]).remove();
        $("#"+page_content_del_list[index]+"_hr").remove();
        delete charts[page_content_del_list[index]];
        delete page_data[page_content_del_list[index]]
    }
}

function fetch_content_element(host_name){
    var req = new XMLHttpRequest();
    var resp;
    
    req.open("GET", '/?fetch_element=true&element='+host_name, false);
    req.onload = function() {
        resp =  JSON.parse(req.responseText);
    }
    req.send(null);

    return resp;
}

$(document).ready(function(){
    for (var host_name in page_data){
        set_collapsible(host_name);
        init_chart(host_name, page_data[host_name]);
    }
    init_pagination();

    ws = new WebSocket(ws_url);

    ws.onmessage = function(e) {
        data = JSON.parse(e["data"]);
        update(data)
    }
    
    ws.onopen = function(ev){
        ws.send(1);
    }
});
