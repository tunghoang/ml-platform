### HOW TO INSTALL ###
# curl https://packages.microsoft.com/keys/microsoft.asc | sudo tee /etc/apt/trusted.gpg.d/microsoft.asc
# curl https://packages.microsoft.com/config/ubuntu/20.04/prod.list | sudo tee /etc/apt/sources.list.d/msprod.list
# sudo apt-get update
# sudo apt-get install mssql-tools unixodbc-dev
# 
# Check for installed odbc drivers at /etc/odbcinst.ini
#
# Connection string template : 
#  "DRIVER={ODBC Driver 17 for SQL Server};Server=10.17.4.74;Database=DTPDB;Port=1433;UID=sa;PWD=DTP@Bdpoc"
import pyodbc
import pandas as pd
import re

class DTP:
  def __init__(self, connString="DRIVER={ODBC Driver 17 for SQL Server};Server=10.17.4.74;Database=DTPDB;Port=1433;UID=sa;PWD=DTP@Bdpoc"):
    self.connString = connString
    self.conn = pyodbc.connect(self.connString)
  def rawQuery(self, sql):
    cursor = self.conn.cursor()
    records = cursor.execute(sql).fetchall()
    cursor.close()
    return records
  def rawExecute(self, sql):
    cursor = self.conn.cursor()
    records = cursor.execute(sql).fetchall()
    cursor.close()
  def query(self, source="MAXIMOPROD", sql=""):
    __sql = f"""SELECT * FROM OPENQUERY({source}, '{re.sub("'","''", sql)}')"""
    return self.rawQuery(__sql)
  def asDataFrame(self, source="MAXIMOPROD", sql="", columns=None):
    records = self.query(source=source, sql=sql)
    return pd.DataFrame.from_records(records, columns=columns)
