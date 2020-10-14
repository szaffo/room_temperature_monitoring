
// Setup listeners
document.addEventListener("DOMContentLoaded", () => {

    document.editor = new Editor()
    document.webSocket = new WebSocket('ws://192.168.0.117:8765');
    document.webSocket.onmessage = function (event) {
     
        data = JSON.parse(event.data)
        document.editor.parseData(data)
    }
    document.webSocket.onopen = function (event) {
        refresh()
    };  
});

const pulse = () => {
    const dot = document.getElementById('dot')
    const newDot = dot.cloneNode(true)
    dot.parentNode.replaceChild(newDot, dot)
}

const refresh = () => {
    document.webSocket.send(`GET after ${document.editor.lastTimestamp / 1000}`)
}


const updateButtonsState = () => {
    document.getElementById('next-btn').disabled = cnt == numOfImages - 1;
    document.getElementById('prev-btn').disabled = cnt == 0;
}

const updateHeader = (text) => document.getElementById('count-holder').innerText = text

class Editor {
    constructor() {
        this.traces = []
        this.tempTrace = {
            name: 'Temperature',
            mode: 'lines',
            line: {
                shape: 'line',
                color: 'rgb(250, 152, 95)',
                width: 1
            },
            type: 'scatter',
            x: [],
            y: [],
        }

        this.hudTrace = {
            name: 'Humidity',
            mode: 'lines',
            line: {
                shape: 'line',
                color: 'rgb(148, 103, 189)',
                width: 1
            },
            type: 'scatter',
            x: [],
            y: [],
            yaxis: 'y2',
        }

        let today = new Date();
        let tommorow = new Date();
        const dd = String(today.getDate()).padStart(2, '0');
        const ddt = String(today.getDate() + 1).padStart(2, '0');
        const mm = String(today.getMonth() + 1).padStart(2, '0'); //January is 0!
        const yyyy = today.getFullYear();

        today = yyyy + '-' + mm + '-' + dd;
        tommorow = yyyy + '-' + mm + '-' + ddt;
        this.today = today
        this.tommorow = tommorow
        this.lastTimestamp = Date.parse(this.today) -2*60*60*1000
        console.log("timestamp at start: ", this.lastTimestamp)


        this.layout = {
            title: 'Disneyland temperature data',
            // showspikes: True,
            xaxis: {
                autorange: false,
                range: [today, tommorow],
                type: 'date',
                title: {
                    text: "Time",
                    standoff: 20
                },
                // xref: 'paper',
                // tick0: today,
                // dtick: 180,
                showspikes: true,
                spikemode: 'toaxis'
            },
            yaxis: {
                autorange: false,

                range: [18, 28],
                type: 'linear',
                dtick: 1,
                title: {
                    text: "Temperature",
                    standoff: 20
                },
                showspikes: true,
                spikemode: 'toaxis',
                titlefont: { color: 'rgb(250, 152, 95)' },
                tickfont: { color: 'rgb(250, 152, 95)' },
            },
            yaxis2: {
                title: 'Humidity',
                titlefont: { color: 'rgb(148, 103, 189)' },
                tickfont: { color: 'rgb(148, 103, 189)' },
                overlaying: 'y',
                side: 'right',
                range: [15, 35],
                dtick: 2,
                showspikes: true,
            }
        }

        const constTrace = {
            name: '22.5°C',
            mode: 'lines',
            line: {
                shape: 'line',
                width: 1
            },
            type: 'scatter',
            x: [today, tommorow],
            y: [22.5, 22.5],
        }

        this.traces.push(this.tempTrace)
        this.traces.push(this.hudTrace)
        this.traces.push(constTrace)
        // this.lastTime = Date.parse('01/25/1999 15:45:00')
        this.init = false
    }

    create(data) {
        pulse()
        this.avgSum = 0;
        this.avgCount = 0;
        
        let element
        for (const index in data.data) {
            element = data.data[index]
            const timestamp = new Date(element.timestamp * 1000)
            
            this.lastTimestamp = (element.timestamp * 1000 > this.lastTimestamp)? element.timestamp * 1000 : this.lastTimestamp
            this.tempTrace.x.push(timestamp)
            this.tempTrace.y.push(element.temperature)
            this.hudTrace.x.push(timestamp)
            this.hudTrace.y.push(element.humidity)

            this.avgSum += element.temperature
            this.avgCount++
        }

        this.avg = this.avgSum / this.avgCount
        this.avgTrace = {
            name: `Average(${Math.round(this.avg * 10) / 10}°C)`,
            mode: 'lines',
            line: { 
                shape: 'line',
                width: 1
            },
            type: 'scatter',
            x: [this.today, this.tommorow],
            y: [this.avg, this.avg],
        }
        this.traces.push(this.avgTrace)
        
        Plotly.newPlot('page', this.traces, this.layout);
        this.init = true
        console.log("Timestamp at the end:", this.lastTimestamp)
        updateHeader(`Temperature: ${Math.round(data.data[data.data.length - 1].temperature * 10) / 10}°C\nHumidity: ${Math.round(data.data[data.data.length - 1].humidity * 10) / 10}%`)
        setInterval(() => {
            refresh()
        }, 3050);
    }
    

    extend(data) {
        pulse()
        // console.log(data)

        let update = {
            x: [[], []],
            y: [[], []]
        }

        let element
        for (const index in data.data) {
           
            element = data.data[index]
            const timestamp = new Date(element.timestamp * 1000)

            this.lastTimestamp = (element.timestamp * 1000 > this.lastTimestamp) ? element.timestamp * 1000 : this.lastTimestamp
           
            update.x[0].push(timestamp)
            update.y[0].push(element.temperature)

            update.x[1].push(timestamp)
            update.y[1].push(element.humidity)
            

            this.avgSum += element.temperature
            this.avgCount++
            

        }

        this.avg = this.avgSum / this.avgCount
        this.avgTrace.y = [this.avg, this.avg]
        this.avgTrace.name = `Average(${Math.round(this.avg * 10) / 10}°C)`
        Plotly.extendTraces('page', update, [0, 1])
        Plotly.deleteTraces('page', 3)
        Plotly.addTraces('page', this.avgTrace)
        if (data.data.length > 0) {
            updateHeader(`Temperature: ${Math.round(data.data[data.data.length - 1].temperature * 10) / 10}°C Humidity = ${Math.round(data.data[data.data.length - 1].humidity * 10) / 10}%`)
        }

    }

    parseData(data) {

        if (this.init) {
            this.extend(data)
        } else {
            this.create(data)
        }
    }

}