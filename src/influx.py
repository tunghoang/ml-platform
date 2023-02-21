import json
import os
import warnings
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
from influxdb_client import InfluxDBClient
from influxdb_client.client.warnings import MissingPivotFunction
from influxdb_client.client.write_api import SYNCHRONOUS

warnings.simplefilter("ignore", MissingPivotFunction)

__client = None
#os.environ["INFLUX_CONFIG_FILE"] = "/opt/home/jupyter-bdpoc/workspace/bdpoc-datahub/config.ini"


def getClient():
  """Get InfluxDB client from config file or environment variable"""
  global __client
  if __client is None:
    __client = InfluxDBClient.from_config_file(os.environ.get('INFLUX_CONFIG_FILE') or "/opt/tljh/ml-platform/etc/db.ini")
  return __client


def getQueryClient():
  """Get InfluxDB query api"""
  return getClient().query_api()

def getWriteClient():
  """Get InfluxDB write api"""
  return getClient().write_api(write_options=SYNCHRONOUS)

class Influx:
  """A supporting class to query data from InfluxDB"""
  def __init__(self, org: Optional[str] = 'BDPOC', fields: Optional["list[str]"] = None, bucket: Optional[str] = 'datahub-test', measurement: Optional[str] = "phdpeer", start: Optional[str] = None, stop: Optional[str] = None, rate: Optional[str] = '30s', timezone: Optional[str] = "Asia/Ho_Chi_Minh", interpolation: Optional[bool] = True):
    """Create a new Influx instance

        Parameters:
        ----------
        + org: Optional[str]
            Organization of InfluxDB. Defaults to &#39;BDPOC&#39;.
        + fields: Optional[&quot;list[str]&quot;]
            An array of filter fields. Defaults to None.
        + bucket: Optional[str]
            Bucket of InfluxDB. Defaults to &#39;datahub-test&#39;.
        + measurement: Optional[str]
            Bucket measurement. Defaults to &quot;phdpeer&quot;.
        + start: Optional[str]
            Start time. Defaults to 10 minutes ago.
        + stop: Optional[str]
            Stop time. Defaults to now.
        + rate: Optional[str]
            Window rate, needed for aggregation (sampling rate). Defaults to &#39;30s&#39;.
        + timezone: Optional[str]
            Timezone, default to &#39;Asia/Ho_Chi_Minh&#39;
        + interpolation: Optional[bool]
            Data will be interpolated if True. Default is True
    """
    self.org = org or 'BDPOC'
    self.bucket = bucket
    self.measurement = measurement
    self.fields = fields or []
    now = datetime.now()
    self.start = start or (now - timedelta(minutes=10))
    self.stop = stop or now
    self.rate = rate
    self.timezone = timezone
    self.interpolation = interpolation
    self.debug = False

  def from_now(self, minutes: int):
    """Set start and stop time for the query relatively with current time
    Parameters:
    ----------
    + minutes: int
        Minutes ago from now
        
    Returns:
    -------
        Influx: The Influx instance
    """
    now = datetime.now()
    self.start = now - timedelta(minutes=minutes)
    self.stop = now
    return self
  
  def addField(self, field: str):
    """Add a field to filter

    Parameters:
    ----------
    + field: str
      String of field name

    Returns:
    -------
      Influx: Influx instance
    """
    if field in self.fields:
      return self
    self.fields.append(field)
    return self

  def addFields(self, fields: "list[str]"):
    """Add a list of fields to filter

    Parameters:
    ----------
    + fields: list[str]
      An array of field names

    Returns:
    -------
      Influx: Influx instance
    """
    self.fields += fields
    return self

  def setStart(self, start: str):
    """Set start time to query

    Parameters:
    ----------
    + start: str
      Start time in ISO format

    Returns:
    -------
      Influx: Influx instance
    """
    self.start = start or self.start
    return self

  def setStop(self, stop: str):
    """Set stop time to query

    Parameters:
    ----------
    + stop: str
      Stop time in ISO format

    Returns:
    -------
      Influx: Influx instance
    """
    self.stop = stop or self.stop
    return self

  def setRate(self, rate: str):
    """Set rate to query with aggregation

    Parameters:
    ----------
    + rate: str
      Rate per window in string format

    Returns:
    -------
      Influx: Influx instance
    """
    self.rate = rate or self.rate
    return self

  def __query(self) -> str:
    """Generate query string

    Returns:
    -------
      str: Query in string format
    """
    q = None
    if len(self.fields) > 0:
      filter_str = " ".join([('or r._field == "' + f + '"') for f in self.fields])
      q = f'''import "interpolate"
from(bucket: "{self.bucket}")
|> range(start: {int(self.start.timestamp())}, stop: {int(self.stop.timestamp())})
|> filter(fn: (r) => r._field == "{self.measurement}" { filter_str })'''
    else:
      q = f'''import "interpolate"
from(bucket: "{self.bucket}")
|> range(start: {int(self.start.timestamp())}, stop: {int(self.stop.timestamp())})'''
      
    if self.interpolation:
      q += f'|> aggregateWindow(every: {self.rate}, fn: mean, createEmpty: false)'
    if self.debug:
      print(q)
    return q

  def __query_min_max(self):
    q = None
    if len(self.fields) > 0:
      filter_str = " ".join([('or r._field == "' + f + '"') for f in self.fields])
      q = f'''from(bucket: "{self.bucket}")
|> range(start: {int(self.start.timestamp())}, stop: {int(self.stop.timestamp())})
|> filter(fn: (r) => r._field == "{self.measurement}" { filter_str })'''
    else:
      q = f'''import "interpolate"
from(bucket: "{self.bucket}")
|> range(start: {int(self.start.timestamp())}, stop: {int(self.stop.timestamp())})'''
    q = f"""data = {q}
maxTable = data |> max()
minTable = data |> min()
union(tables: [maxTable, minTable])"""
    
    if self.debug:
      print(q)
    return q
  
  def asDataFrame(self) -> pd.DataFrame:
    """Query data from InfluxDB and return as DataFrame

    Returns:
    -------
      pd.DataFrame: DataFrame of query result with time formatted by timezone
    """
    results = getQueryClient().query_data_frame(self.__query(), self.org)
    if results.empty:
      return results
    if type(results) == list:
      results = results.concat()
    results['_time'] = results._time.dt.tz_convert(self.timezone)
    results['_start'] = results._time.dt.tz_convert(self.timezone)
    results['_stop'] = results._time.dt.tz_convert(self.timezone)
    return results

  def asPivotDataFrame(self) -> pd.DataFrame:
    """Query data from InfluxDB do pivot and return a DataFrame
    
    Returns:
    -------
      pd.DataFrame: DataFrame of query result with pivot data
    """
    results = self.asDataFrame().pivot(index="_time", columns="_field", values="_value")
    results["_time"] = results.index
    results = results.reset_index(drop=True)
    
    return results
  
  def asMinMaxDataFrame(self) -> pd.DataFrame:
    results = getQueryClient().query_data_frame(self.__query_min_max(), self.org)
    return results
  
  def setInterpolation(self, interpolation: bool) : 
    """Set interpolation
    
    Parameters:
    ----------
    + interpolation: bool
      interpolation property of the Influx instance. If interpolation is True, output data will be interpolated. Default to True
    Returns:
    -------
      Influx: the Influx instance
    """
    self.interpolation = interpolation
    return self
  
  def setBucket(self, bucket: str): 
    """Set read bucket
    
    Parameters:
    ----------
    + bucket: str
      The bucket name that the Influx instance will read from. Default to datahub-test
    Returns:
    -------
      Influx: the Influx instance
    """
    self.bucket = bucket
    return self
  def setDebug(self, debug):
    self.debug = debug
    return self
  
class InfluxWriter:
  """A supporting class to write data to InfluxDB"""
  def __init__(self, org: Optional[str] = 'BDPOC', bucket: Optional[str] = 'check-datahub', precision: Optional[str] = 's', timezone: Optional[str] = "Asia/Ho_Chi_Minh"):
    """Create a new Influx instance

        Parameters:
        ----------
        + org: Optional[str]
            Organization of InfluxDB. Defaults to &#39;BDPOC&#39;.
        + bucket: Optional[str]
            Bucket of InfluxDB. Defaults to &#39;check-datahub&#39;.
        + timezone: Optional[str]
            Timezone, default to &#39;Asia/Ho_Chi_Minh&#39;
    """
    self.org = org or 'BDPOC'
    self.bucket = bucket
    self.timezone = timezone
    self.precision = precision
  def setBucket(self, bucket: str):
    """Set write bucket for the InfluxWriter instance
        Parameters:
        ----------
        + bucket: str
            The write bucket
            
        Returns:
        -------
            InfluxWriter: The InfluxWriter instance
    """
    self.bucket = bucket
    return self
  
  def setPrecision(self, precision: str):
    """Set write bucket for the InfluxWriter instance
        Parameters:
        ----------
        + precision: str
            Time precision. Acceptable values are &#39;s&#39;,&#39;ms&#39;, &#39;us&#39;, &#39;ns&#39;
            
        Returns:
        -------
            InfluxWriter: The InfluxWriter instance
    """
    self.precision = precision
    return self
  
  def write(self, point):
    getWriteClient().write(bucket=self.bucket, org=self.org, precision=self.precision, record=point)