import select
import asyncio
import websockets
import sys
from peewee import *
import multiprocessing
import datetime
import Adafruit_DHT
import time
import traceback
import json

# Consts
TIME_BETWEEN_MEASUREMENTS = 3
MAX_TEMPERATURE_DELTA_PER_SEC = 10
MAX_HUMIDITY_DELTA_PER_SEC = 15
FLATTEN_RATE = 20
DHT_SENSOR = Adafruit_DHT.DHT22
DHT_PIN = 4

# Globals
flattenTemp = [0 for x in range(FLATTEN_RATE)]
flattenHumi = [0 for x in range(FLATTEN_RATE)]
db = SqliteDatabase('dht.db')


def fillFlatten():
    global flattenTemp
    global flattenHumi

    lastMeasurements = [m for m in Measurement.select().order_by(
        Measurement.timestamp).limit(FLATTEN_RATE).execute()]

    if len(lastMeasurements) == 0:
        print("No measurements. Filling with 22.5")
        flattenTemp = [22.5 for x in range(FLATTEN_RATE)]
        flattenHumi = [0 for x in range(FLATTEN_RATE)]
        return


    elif len(lastMeasurements) < FLATTEN_RATE:

        lastMeasurements = lastMeasurements + [lastMeasurements[len(lastMeasurements) - 1]
            for x in range(FLATTEN_RATE - len(lastMeasurements))]

    flattenTemp = [m.temperature for m in lastMeasurements]
    flattenHumi = [m.humidity for m in lastMeasurements]


def getTimestamp():
    return datetime.datetime.timestamp(datetime.datetime.now())


def getTodaysTimestamp():
    d = datetime.datetime.now()
    today = datetime.datetime(d.year, d.month, d.day).timestamp()
    return today


def rotate(l):
    return [l[-1]] + l[0:-1]


def measure():
    global flattenHumi
    global flattenTemp

    humidity, temperature = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)
    
    if humidity == None or temperature == None:
        raise ValueError("Can't read from sensor")

    lastmt = flattenTemp[-1] if not flattenTemp[-1] == 0 else temperature 
    lastmh = flattenHumi[-1] if not flattenHumi[-1] == 0 else humidity 
    
    if abs(lastmt - temperature) > MAX_TEMPERATURE_DELTA_PER_SEC:
        raise ValueError("Temperature propably not correct")

    if abs(lastmh - humidity) > MAX_HUMIDITY_DELTA_PER_SEC:
        raise ValueError("Humidity propably not correct")

    flattenTemp = rotate(flattenTemp)
    flattenHumi = rotate(flattenHumi)

    flattenTemp[0] = temperature
    flattenHumi[0] = humidity

    avgTemperaute = sum(flattenTemp) / FLATTEN_RATE
    avgHumidity = sum(flattenHumi) / FLATTEN_RATE

    Measurement.create(temperature=avgTemperaute, rawTemperature=temperature, humidity=avgHumidity, rawHumidity=humidity).save()
    print("Succesfull measurement. Temperature={}, Humiditiy={}, rawTemperature={}, rawHumidity={}".format(avgTemperaute, avgHumidity, temperature, humidity))



def repeateMeasurement():
    while True:
        try:
            measure()
        except ValueError as e:
            print(e)
            print('Error in measurement, repeating later')
            time.sleep(2)
                
        else:
            time.sleep(TIME_BETWEEN_MEASUREMENTS)


def startMeasuring():
    print("Opening the DB and starting to measure.")
    db.connect()
    try:
        fillFlatten()
        repeateMeasurement()
    except KeyboardInterrupt as e:
        print("\nProgram stopped manually")
    except Exception as e:
        traceback.print_exc()
        print("Error while measurements. Closing database")
    finally:
        print("Closing the database")
        db.close()

def getMeasurementsAfter(timestamp):
    timestamp = int(timestamp)
    cursor = Measurement.select().where(Measurement.timestamp > timestamp).execute()
    measurements = [{
        "temperature": m.temperature,
        "humidity": m.humidity,
        "timestamp": m.timestamp.timestamp(),
        "rawTemperature": m.rawTemperature,
        "rawHumidity": m.rawHumidity
    } for m in cursor]
    return {
        "data": measurements,
        "timestamp": timestamp
    }


class Measurement(Model):
    temperature = FloatField()
    humidity = FloatField()
    rawTemperature = FloatField()
    rawHumidity = FloatField()
    timestamp = TimestampField(default=getTimestamp)

    def __repr__(self):
        return "<Measurement temp={}, humi={}, timestamp={}>".format(self.temperature, self.humidity, self.timestamp)

    class Meta:
        database = db


async def handler(websocket, path):
    async for message in websocket:
        print("Message on socket: {}".format(message))
        if message[:9] == "GET after":
            timestamp = message.split(' ')[2]
            await websocket.send(json.dumps(getMeasurementsAfter(timestamp)))

def startSocket():
    print("Starting the server")
    start_server = websockets.serve(handler, "0.0.0.0", 8765)
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()



if __name__ == "__main__":
    print("Starting the app")
    measurer = multiprocessing.Process(target=startMeasuring, name="Measurer")
    measurer.start()
    startSocket()

    # db.connect()
    # db.create_tables([Measurement])
    # db.close()


    # startSocket()



