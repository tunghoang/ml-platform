import json
import os
import warnings
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
from influxdb_client import InfluxDBClient
from influxdb_client.client.warnings import MissingPivotFunction

warnings.simplefilter("ignore", MissingPivotFunction)

__client = None
os.environ["INFLUX_CONFIG_FILE"] = "/opt/home/jupyter-bdpoc/workspace/bdpoc-datahub/config.ini"


def getClient():
  """Get InfluxDB client from config file or environment variable"""
  global __client
  if __client is None:
    __client = InfluxDBClient.from_config_file(os.environ.get('INFLUX_CONFIG_FILE') or "/opt/tljh/ml-platform/etc/db.ini")
  return __client


def getQueryClient():
  """Get InfluxDB query api"""
  return getClient().query_api()


class Influx:
  """A supporting class to query data from InfluxDB"""
  def __init__(self, org: Optional[str] = 'BDPOC', fields: Optional["list[str]"] = None, bucket: Optional[str] = 'datahub-test', measurement: Optional[str] = "phdpeer", start: Optional[str] = None, stop: Optional[str] = None, rate: Optional[str] = '30s'):
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
		"""
    self.org = org or 'BDPOC'
    self.bucket = bucket
    self.measurement = measurement
    self.fields = fields or []
    now = datetime.now()
    self.start = start or (now - timedelta(minutes=10))
    self.stop = stop or now
    self.rate = rate
    self.DEFAULT_TIMEZONE = os.environ.get("INFLUX_QUERY_TIMEZONE") or 'Asia/Ho_Chi_Minh'

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

  def asDataFrame(self) -> pd.DataFrame:
    """Query data from InfluxDB and return as DataFrame

    Returns:
    -------
      pd.DataFrame: DataFrame of query result with time formatted by timezone
    """
    results = getQueryClient().query_data_frame(self.__query(), self.org)
    if type(results) == list:
      results = results.concat()
    results['_time'] = results._time.dt.tz_convert(self.DEFAULT_TIMEZONE)
    results['_start'] = results._time.dt.tz_convert(self.DEFAULT_TIMEZONE)
    results['_stop'] = results._time.dt.tz_convert(self.DEFAULT_TIMEZONE)
    return results
