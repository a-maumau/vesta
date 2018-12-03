// general setting for charts
if (!Highcharts.theme){
    Highcharts.setOptions({
        chart: {
            backgroundColor:'rgba(255, 255, 255, 0.0)',
            height: 280,
            width:280,
        },
        colors: ["#f62366", "#ea49ad", "#be74e5", "#7697ff", "#00b0ff", "#00c1f2", "#0ccdd6"],
        title: {
          style: {
            color: '#f62366'
          }
        },
        legend: {
          itemStyle: {
            fontSize: '24px'
          }
        }
    });
}

function create_mem_usage_gauge(id_name, max_val, min_val){
    return Highcharts.chart(id_name, {
        borderWidth:300,
        chart: {
            spacingLeft: 0,
            type: 'solidgauge',
            height: '100%',
        },

        // hide credits and buttom
        credits: {enabled: false},
        exporting:{ enabled: false },

        title: {
            text: 'Mem. Usage',
            margin: 0,
            align: 'center',
            x: 0,
            y: 5,
            floating: true,
            style: {
                fontSize: '32px'
            }
        },
        tooltip: {
            borderWidth: 0,
            backgroundColor: 'none',
            shadow: false,
            align: "center",
            style: {
            fontSize: '31px'
            },
            pointFormat: '{series.name}<br><span style="font-size:1.5em; color: {point.color}; font-weight: bold; text-align:right;">{point.y}%</span>',
            positioner: function (labelWidth) {
                return {
                    x: (this.chart.chartWidth - labelWidth) / 2,
                    y: (this.chart.plotHeight / 2) -55
                };
            }
        },
        pane: {
            startAngle: 0,
            endAngle: 360,
            background: [{
                outerRadius: '108%',
                innerRadius: '78%',
                backgroundColor: Highcharts.Color("#555555")
                .setOpacity(1.0)
                .get(),
                borderWidth: 0,
            }]
        },
        yAxis: {
            min: 0,
            max: 103,
            lineWidth: 0,
            tickPositions: []
        },
        plotOptions: {
            solidgauge: {
                dataLabels: {
                    enabled: false
                },
                linecap: 'round',
                stickyTracking: false,
                rounded: true,
                borderWidth: 300,
            }   
        },
        legend: {
            enabled: false,
            align: "center",
            margin: 0,
            verticalAlign: 'bottom',
            floating: true,
            x: 0,
            y: 30,
            itemStyle: {
                fontSize:'30px',
            },
        },
        series: [{
            marker: {
                symbol: 'square', // Make it a square
                fillColor: "#f62366",
            },
            lineWidth: 0, // With no line going through it
            name: 'max',
            data: [{
                color: "#f62366",
                radius: '108%',
                innerRadius: '90%',
                y: max_val
            }],
            showInLegend: true
        },{
            marker: {
                symbol: 'square', // Make it a square
                fillColor: '#4bb',
            },
            lineWidth: 0, // With no line going through it
            name: 'min',
            data: [{
                color: "#4bb",
                radius: '88%',
                innerRadius:
                '78%',
                y: min_val
            }],
            showInLegend: true
        }]
    });
}

function create_volatile_gauge(id_name, max_val, min_val){
    return Highcharts.chart(id_name, {
        borderWidth:300,
            chart: {
            spacingLeft: 0,
            type: 'solidgauge',
            height: '100%',
        },

        // hide credits and buttom
        credits: {enabled: false},
        exporting:{ enabled: false },

        title: {
            text: 'Volatile',
            margin: 0,
            align: 'center',
            x: 0,
            y: 5,
            floating: true,
            style: {
                fontSize: '31px'
            }
        },
        tooltip: {
            borderWidth: 0,
            backgroundColor: 'none',
            shadow: false,
            align: "center",
            style: {
                fontSize: '32px'
            },
            pointFormat: '{series.name}<br><span style="font-size:1.5em; color: {point.color}; font-weight: bold; text-align:right;">{point.y}%</span>',
            positioner: function (labelWidth) {
                return {
                    x: (this.chart.chartWidth - labelWidth) / 2,
                    y: (this.chart.plotHeight / 2) -60
                };
            }
        },
        pane: {
            startAngle: 0,
            endAngle: 360,
            background: [{
                outerRadius: '108%',
                innerRadius: '78%',
                backgroundColor: Highcharts.Color("#555555")
                .setOpacity(1.0)
                .get(),
                borderWidth: 0,
            }]
        },
        yAxis: {
            min: 0,
            max: 103,
            lineWidth: 0,
            tickPositions: []
        },
        plotOptions: {
            solidgauge: {
                dataLabels: {
                enabled: false
            },
            linecap: 'round',
            stickyTracking: false,
            rounded: true,
            borderWidth: 300,
            }
        },
        legend: {
            align: "center",
            margin: 0,
            verticalAlign: 'bottom',
            floating: true,
            x: 0,
            y: 25,
            itemStyle: {
                fontSize:'30px',
            },
        },
        series: [{
            marker: {
                symbol: 'square', // Make it a square
                fillColor: "#f62366",
            },
            lineWidth: 0, // With no line going through it
            name: 'max',
            data: [{
                color: "#f62366",
                radius: '108%',
                innerRadius: '90%',
                y: max_val
            }],
            showInLegend: true
        },{
            marker: {
                symbol: 'square', // Make it a square
                fillColor: '#4bb',
            },
            lineWidth: 0, // With no line going through it
            name: 'min',
            data: [{
                color: "#4bb",
                radius: '88%',
                innerRadius:
                '78%',
                y: min_val
            }],
            showInLegend: true
        }]
    });
}

function create_temperature_gauge(id_name, max_val, min_val){
    return Highcharts.chart(id_name, {
        chart: {
            type: 'gauge',
            plotBackgroundColor: null,
            plotBackgroundImage: null,
            plotBorderWidth: 0,
            plotShadow: false,
        },
        title: {
            text: 'Temperature',
            y: 5,
            floating: true,
            style: {
                fontSize: '32px'
            }
        },
        
        // hide credits and buttom
        credits: {enabled: false},
        exporting:{ enabled: false },

        // it seems tooltip must come faster than series to enable
        tooltip: {
            valueSuffix: ' °C',
            style: {
                fontSize: '32px'
            },
            pointFormat: '{point.name}<br><span style="font-size:1.5em; color: {point.dial.backgroundColor}; font-weight: bold; text-align:right;">{point.y}</span>',
            positioner: function (labelWidth) {
                return {
                    x: (this.chart.chartWidth - labelWidth) / 2,
                    y: (this.chart.plotHeight / 2) -55
                };
            }
        },
        pane: {
            startAngle: -150,
            endAngle: 150,
            background: [{
                backgroundColor: {
                    linearGradient: { x1: 0, y1: 0, x2: 0, y2: 1 },
                    stops: [
                        [0, '#FFF'],
                        [1, '#333']
                    ]
                },
                borderWidth: 0,
                outerRadius: '109%'
            }, {
                backgroundColor: {
                    linearGradient: { x1: 0, y1: 0, x2: 0, y2: 1 },
                    stops: [
                        [0, '#333'],
                        [1, '#FFF']
                    ]
                },
                borderWidth: 1,
                outerRadius: '107%'
            }, {
                // default background
                // do not erase here.
            }, {
                backgroundColor: '#DDD',
                borderWidth: 0,
                outerRadius: '105%',
                innerRadius: '103%'
            }]
        },
        // the value axis
        yAxis: {
            min: 0,
            max: 120,

            minorTickInterval: 'auto',
            minorTickWidth: 1,
            minorTickLength: 10,
            minorTickPosition: 'inside',
            minorTickColor: '#666',

            tickPixelInterval: 30,
            tickWidth: 2,
            tickPosition: 'inside',
            tickLength: 10,
            tickColor: '#666',
            labels: {
                step: 4,
                rotation: 'auto',
                style: {
                    fontSize: "20px"
                }
            },
            title: {
                text: '°C',
                fontSize: "32px",
                y: 20,
                style: {
                    fontSize: '32px',
                },
            },
            plotBands: [{
                from: 0,
                to: 60,
                //color: '#55BF3B', // green
                color: '#555555'
            }, {
                from: 60,
                to: 90,
                //color: '#DDDF0D' // yellow
                color: '#555555'
            }, {
                from: 90,
                to: 120,
                //color: '#DF5353' // red
                color: '#555555'
            }]
        },
        series: [{
            type: 'gauge',
            name: 'Temperature',
            data: [{
                name: 'max',
                y: max_val,
                dial: {
                    radius: '100%',
                    baseWidth: 4,
                    baseLength: '100%',
                    rearLength: 0,
                    backgroundColor: '#f62366',
                }
            }, {
                name: 'min',
                y: min_val,
                dial: {
                    radius: '100%',
                    baseLength: '100%',
                    rearLength: 0,
                    backgroundColor: '#4bb',
                }
            }],
            dataLabels: {
                enabled: false,
            },
        }]
    });
}

function create_mem_usage_detail_pie(id_name, pie_data, used, total){
    /***********************************
        pie_data is like,
        [
            ['C', 9999],
            ['python', 2780],
            ['C++', 8800],
            ['Rust', 1450],
            {
                name: 'Available',
                color: "#888888"
                y: 349,
                dataLabels: {
                    enabled: false
                }
            }
        ]
    ************************************/
    
    return Highcharts.chart(id_name, {
        chart: {
            plotBackgroundColor: null,
            plotBorderWidth: 0,
            plotShadow: false
        },

        // hide it
        credits: {enabled: false},
        exporting:{ enabled: false },

        title: {
            text: 'Memory<br>Usage<br><p style="color: #000">'+String(used)+'/'+String(total)+'</p><br>MiB',
            align: 'center',
            verticalAlign: 'middle',
            y: -25,
        },
        tooltip: {
            borderRadius: 10,
            style: {
                fontSize: 20
            },
            formatter: function () {
                return this.point.name +': '+ this.point.y +'MiB'+' ('+this.point.percentage.toFixed(1)+"%"+')';
            },
        },
        plotOptions: {
            pie: {
                dataLabels: {
                    enabled: false,
                    distance: -20,
                },
                startAngle: 0,
                endAngle: 360,
                center: ['50%', '50%'],
                size: '110%'
            }
        },
        series: [{
            type: 'pie',
            name: 'Used Memory',
            innerSize: '60%',
            data: pie_data
        }]
    });
}