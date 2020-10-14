import Adafruit_DHT
import time
import asyncio
import websockets
import json
import asyncio
import websockets
from datetime import datetime
from threading import Thread

MAX_TEMPERATURE_DELTA_PER_SEC = 2
FLATTEN_RATE = 20
lastTemp = None
lastHud = None

infoTemp, infoHud = 0.0,0.0

def loadHistotry():
    with open('/home/pi/dht/history.json', 'r') as f:
        data = json.load(f)

    return data

def getDateFormatted():
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")
    return current_time


def saveToHistory(data, temp, humidity):
    record = {
        "temperature": temp,
        "humidity": humidity, 
        "timeFormatted": getDateFormatted(),
        "time":  datetime.now().hour * 60 + datetime.now().minute
    }

    today = str(datetime.now().date())
    if not today in data["history"]:
        data["history"][today] = []

    data["history"][today].append(record)

    writer = Thread(target=write, args=(data, ), name="Data writer")
    writer.start()
    writer.join()
    # write(data)

    return data

def write(data):
    with open('/home/pi/dht/history.json', 'w') as f:
        json.dump(data, f, indent=4)


# ------------------------------------------------------------------

DHT_SENSOR = Adafruit_DHT.DHT22
DHT_PIN = 4

tempData = loadHistotry()
temps = [0 for x in range(FLATTEN_RATE)]
huds = [0 for x in range(FLATTEN_RATE)]

def rotate(l, n):
    return l[n:] + l[:n]

def getHudTemp():
    global lastTemp
    global lastHud
    global temps
    global huds
    global infoHud
    global infoTemp

    humidity, temp = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)
    while (humidity == None or temp == None):
        time.sleep(0.01)
        humidity, temp = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)

    
    if lastTemp == None:
        temps = [temp for x in range(FLATTEN_RATE)]
        huds = [humidity for x in range(FLATTEN_RATE)]
    else:
        if abs(lastTemp - temp) > MAX_TEMPERATURE_DELTA_PER_SEC:
            humidity, temp = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)
    
    lastTemp = temp
    lastHud = humidity
    infoHud = humidity
    infoTemp = temp
    temps = rotate(temps, 1)
    huds = rotate(huds, 1)
    temps[len(temps) - 1] = temp
    huds[len(temps) - 1] = humidity
    avgTemp = sum(temps) / len(temps)
    avgHud = sum(huds) / len(huds)

    return (avgHud, avgTemp)


def getHudtempString():
    return "Temperature: {0:0.1f}°C  Humidity: {1:0.1f}%".format(infoTemp, infoHud)


async def echo(websocket, path):
    print("Server is on")
    async for message in websocket:
        if message == 'GET info':
            try:
                # await websocket.send(str(getHudtempString()))
            except:
                print("Can't send data")
        elif message == 'GET history':
            try:
                data = tempData['history'][list(tempData[history].keys())[-1]]
                await websocket.send(json.dumps(data))
            except:
                print("Can't send data")


async def periodic():
    global tempData
    while True:
        humidity, temperature = getHudTemp()
        tempData = saveToHistory(tempData, temperature, humidity)
        await asyncio.sleep(3)

loop = asyncio.get_event_loop()
task = loop.create_task(periodic())

loop.run_until_complete(websockets.serve(echo, '0.0.0.0', 8765))
loop.run_until_complete(task)

loop.run_forever()


