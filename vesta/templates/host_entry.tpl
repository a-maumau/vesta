<div class="collapsible host_info {% if host_status not in ok_statuses %}bad_status{% endif %}" id="{{ host_name }}">
    {% if host_status not in ok_statuses %}
    <h2 class="bad_status_head">### {{ host_status }} ###</h2>
    {% endif %}
    <h3 class="host_name_head">{{ host_name }}<small>{{ host_ip }}</small></h3>
    <p class="timestamp">last update: {{ timestamp }}</p>
    <div class="row">
        <div class="col-md-6 host_info">
            <div class="summary_graph_wrapper">
                <div class="host_summary_graph" id="{{ host_name }}_mem_gauge"></div>
                <div class="host_summary_graph" id="{{ host_name }}_vol_gauge"></div>
                <div class="host_summary_graph" id="{{ host_name }}_temp_gauge"></div>
            </div>
        </div>
        <div class="col-md-6 sub_info">
            <div class="table_area table_area_sub_info">
                <table class="info_table sub_info_table" id="{{ host_name }}_sub_info_table">
                    <thead>
                        <tr>
                            <th class="tc_gpu_name">GPU</th>
                            <th class="tc_free_mem value">free mem.</th>
                            <th class="tc_volatile value">vol.</th>
                            <th class="tc_temperature value">temp.</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for gpu_id, data in gpu_info.items() %}
                        <tr id="{{ host_name }}_{{ gpu_id }}_gpu_info">
                            <td class="tc_gpu_name">{{ gpu_id }}</td>
                            <td class="tc_free_mem value">{{ data.available_memory }}MiB</td>
                            <td class="tc_volatile value">{{ data.gpu_volatile }}%</td>
                            <td class="tc_temperature value">{{ data.temperature }}°C</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    <div class="content">
    {% if host_status in ok_statuses %}
        {% for gpu_id, data in gpu_info.items() %}
        <div class="gpu_entry {{ "last_entry" if loop.last }}" id="{{ host_name }}_{{ gpu_id }}_entry">
            <h4 class="gpu_info_head">{{ gpu_id }}<small>{{ data.gpu_name }}</small></h4>
            <p class="gpu_info_text">available {{ data.available_memory }} MiB, volatile {{ data.gpu_volatile }}%, temperature {{ data.temperature }}°C</p>
            <div class="gpu_memory_deatil">
                <div class="gpu_mem_pie" id="{{ host_name }}_{{ gpu_id }}_mem_pie"></div>
                <div class="table_area table_area_detail_info">
                    <table class="info_table" id="{{ host_name }}_{{ gpu_id }}_process_info_table">
                        <thead>
                            <tr>
                                <th class="tc_command_name">command</th>
                                <th class="tc_user_name">user</th>
                                <th class="tc_used_memory value">used mem.</th>
                            </tr>
                        </thead>
                        <tbody id="{{ host_name }}_{{ gpu_id }}_processes">
                            {% for process_data in data.processes %}
                            <tr id="{{ host_name }}_pid_{{ process_data.pid }}">
                                <td class="tc_command_name">{{ process_data.name }}</td>
                                <td class="tc_user_name">{{ process_data.user }}</td>
                                <td class="tc_used_memory value">{{ process_data.used_memory }}MiB</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        {% endfor %}
    {% endif %}
    </div>
</div>
<hr id="{{ host_name }}_hr">