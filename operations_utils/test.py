import datetime
import time
import pyodbc
import statistics
import numpy as np

arr = [5,10,20,150,100]
fh = open("test.log","a")
fh.write ("Starting the log...\n")

print("arr : ", arr)  
print("50th percentile of arr : ",  
       int(np.percentile(arr, 50))) 
print("25th percentile of arr : ", 
       np.percentile(arr, 25)) 
print("75th percentile of arr : ", 
       np.percentile(arr, 75)) 

print(round(statistics.stdev([1,2,3,4,4,4,5,6]),3))

print ("One day behind ", datetime.datetime.today() + datetime.timedelta(days = -1))

tm = datetime.datetime.fromtimestamp(1591210880000/1000.0).strftime('%Y-%m-%d %H:%M:%S')
print (tm)

tm = datetime.datetime.strftime(datetime.datetime.now(),'%Y-%m-%d %H:%M:%S')
milisec = int(datetime.datetime.now().timestamp() * 1000)

print(milisec)

# to get top of the hour
tm = datetime.datetime.strptime(tm,'%Y-%m-%d %H:%M:%S')
print (tm.hour)
print (datetime.datetime.strftime(tm,'%b-%Y'))
print (datetime.datetime.strftime(tm,'%Y-%m-%d'))

onehourlater = datetime.datetime.today() + datetime.timedelta(hours = -1)
tophour = onehourlater.hour
strtophour = str(tophour) + ":00:00"
strcurrentdate = onehourlater.date()

startdate = str(onehourlater.date()) + " 00:00:00"
enddate = str(onehourlater.date()) + " " + strtophour

startdatem = datetime.datetime.strptime(startdate,'%Y-%m-%d %H:%M:%S')
startdatetm = int(startdatem.timestamp() * 1000)
print (startdatetm)

enddatem = datetime.datetime.strptime(enddate,'%Y-%m-%d %H:%M:%S')
endatetm = int(enddatem.timestamp() * 1000)
print (endatetm)
#print (strtophour,strcurrentdate, datetime.datetime.today() )
print(datetime.datetime.strftime(onehourlater, '%Y-%m-%d %H:%M:%S'))

# 300sec addition
secsadded = datetime.datetime.today() + datetime.timedelta(seconds=300)
print (datetime.datetime.today(), secsadded)

strval = "Hi how are you \
i am fine"
print (strval)

cnxn = pyodbc.connect("Driver={ODBC Driver 17 for SQL Server};"
                      "Server=VM0DWEAIDBD0001.corp.chartercom.com;"
                      "Database=EWSMetrics;"
                      "UID=svc_metrics;"
                      "PWD=tL7sf1htoNxLyJ;")


cursor = cnxn.cursor()
#sqlstr = "INSERT INTO app_users (app_users_name, app_users_desc, app_users_created) values ('Sushant Kumar','Admin Role',current_timestamp)"
#cursor.execute(sqlstr)
#cnxn.commit()

execrow = cursor.execute('SELECT * FROM appd_metric_datacol_type')
cursor.execute('SELECT * FROM appd_metric_datacol_type')
results = cursor.fetchall()
print (len(results))
for row in results:
    print('row = %r' % (row,))
    print('Name: %r'  %(row[1]) )
    print('Name: ',  row[1])

cursor.close()

fh.write ("Ending the log...\n")
fh.close
