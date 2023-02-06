from datetime import datetime, timedelta
from influxdb_client import InfluxDBClient
import json
import warnings
from influxdb_client.client.warnings import MissingPivotFunction

warnings.simplefilter("ignore", MissingPivotFunction)

__client = None
def getClient():
    global __client
    if __client is None:
        __client = InfluxDBClient.from_config_file("/opt/tljh/ml-platform/etc/db.ini")
    return __client

def getQueryClient():
    return getClient().query_api()

class Influx:
    def __init__(self, org='BDPOC', fields = None, bucket='datahub-test', measurement="phdpeer", start=None, stop=None, rate='30s'):
        self.org = org or 'BDPOC'
        self.bucket = bucket
        self.measurement = measurement
        self.fields = fields or []
        now = datetime.now()
        self.start = start or (now - timedelta(minutes=10))
        self.stop = stop or now
        self.rate = rate
    def addField(self, field):
        if field in self.fields: 
            return self
        self.fields.append(field)
        return self
    def addFields(self, fields):
        self.fields += fields
        return self
    def setStart(self, start):
        self.start = start or self.start
        return self
    def setStop(self, stop):
        self.stop = stop or self.stop
        return self
    def setRate(self, rate):
        self.rate = rate or self.rate
        return self
    def __query(self):
        filter_str = " ".join([('or r._field == "' + f + '"') for f in self.fields])
        q = f'''
import "interpolate"
from(bucket: "{self.bucket}")
|> range(start: {int(self.start.timestamp())}, stop: {int(self.stop.timestamp())})
|> filter(fn: (r) => r._field == "{self.measurement}" { filter_str })
|> aggregateWindow(every: {self.rate}, fn: mean, createEmpty: false)
|> interpolate.linear(every: {self.rate})
        '''
        print(q)
        return q
    def asDataFrame(self):
        results = getQueryClient().query_data_frame(self.__query(), self.org)
        if type(results) == list:
            results = results.concat()
        results['_time'] = results._time.dt.tz_convert('Asia/Ho_Chi_Minh')
        return results