<p class="timestamp">last update: {{ timestamp }}</p>
<div class="row">
    <div class="col-lg-12">
        <div class="">
            <table class="info_table gpu_table">
                {% for host_name, host_data in table_data.items() %}
                <thead>
                    <tr>
                        <th colspan="3" class="gpu_table_noborder">{{ host_name }} ({{ host_data.ip_address }})</th>
                    </tr>
                </thead>
                <thead>
                    <tr>
                        <th class="gpu_table_gpu_head gt_gpu_id">GPU ID</th>
                        <th class="gpu_table_gpu_head">GPU Name</th>
                        <th class="gpu_table_gpu_head gt_gpu_mem_size">Memory Usage</th>
                    </tr>
                </thead>
                <tbody>
                    {% for gpu_id, data in host_data["data"][0]["gpu_data"].items() %}
                    <tr>
                        <td class="">{{ data.device_num }}</td>
                        <td class="">{{ data.gpu_name }}</td>
                        <td class="value">{{ data.used_memory }} / {{ data.total_memory }} MiB</td>
                    </tr>
                    {% endfor %}
                    <tr>
                        <td class=""></td>
                        <td class=""></td>
                        <td class="value"></td>
                    </tr>
                </tbody>
            {% endfor %}
            </table>
        </div>
    </div>
</div>