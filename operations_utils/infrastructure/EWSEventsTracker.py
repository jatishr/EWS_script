# Description: This python script will insert/update data into ews_certs_password_expr and vip_api_datasource_hist.
# The script will run everyday and will check if certs or password validto is <= 45 days
# drop mail 
# Version: 1.0
# Date: 9/28/2021
# Author: Sushant Kumar
import subprocess
import datetime
import configparser
import pyodbc
import openpyxl
import re
import os
import sys
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

# pull the configuration file

mconfig = configparser.ConfigParser()
mconfig.read("eventstracker.ini")

# create global variables
# initialize dictionary

conn = mconfig["events_db"]
env = mconfig["events_env"]

dept = ""

def send_email(mail_body, subject, filename, recipient):
    fromaddr = "ews_webservices_operations@charter.com"
    
    msg = MIMEMultipart()

    msg['From'] = fromaddr
    msg['To'] = recipient
    
    if(subject):
        msg['Subject'] = subject
    else:
        msg['Subject'] = "subject of mail."

    body = mail_body

    msg.attach(MIMEText(body, 'html'))

    # Open a file in binary mode
    #with open(filename, "rb") as attachment:
        # Add file as application/octet-stream
        # Email client can usually download this automatically as attachment
    #    part = MIMEBase("application","octet-stream")
    #    part.set_payload(attachment.read())

    # Encode file in ASCII characters to send by email  
    # encoders.encode_base64(part)

    # Add attachment to message and convert message to string
    #part.add_header(
    #    "Content-Disposition",
    #    f"attachment; filename= {filename}",
    #)

    #msg.attach(part)
    #text = msg.as_string()
    
    s = smtplib.SMTP('mailrelay.chartercom.com', 25)
    s.starttls()   
    text = msg.as_string()
    s.sendmail(fromaddr, recipient, text)
    s.quit()
    
def gettimestrategy(strategy):
    #return start date and end date
    dates = []
    currentdatetm = datetime.datetime.today()
    startdatetm = str(currentdatetm.date()) + " 00:00:00"

    # find will give negative if no data found
    if strategy.find('today') >= 0:
        startdatetm = str(currentdatetm.date()) + " 00:00:00"
        enddatetm = str(currentdatetm.date()) +" " + str(currentdatetm.hour) + ":00:00"

    if strategy.find('yesterday') >= 0:
        d = datetime.datetime.today() + datetime.timedelta(days = -1)
        startdatetm = datetime.datetime.strftime(d,'%Y-%m-%d') + " 00:00:00"        
        enddatetm = datetime.datetime.strftime(d,'%Y-%m-%d') + " 23:59:59"

    if strategy.find('weekly') >= 0:
        d = datetime.datetime.today() + datetime.timedelta(days = - 7)
        startdatetm = datetime.datetime.strftime(d,'%Y-%m-%d') + " 00:00:00"
        enddatetm = datetime.datetime.strftime(d,'%Y-%m-%d') + " 23:59:59"

    if strategy.find('yeartodate') >= 0:
        #check the year and start time will be start of the year
        d = datetime.datetime.today() + datetime.timedelta(days = -7)
        startdatetm = str(d.year) + "-01-01" + " 00:00:00"
        # since timer will run on monday we will take last week's saturday into account
        d = datetime.datetime.today() + datetime.timedelta(days = -2)
        enddatetm = datetime.datetime.strftime(d,'%Y-%m-%d') + " 23:59:59"

    if strategy.find('tonight') >= 0:
        # the date time will be 24 hours ahead of the time
        startdatetm = str(currentdatetm.date()) + " 00:00:00"

        # this hack is for server if clock time is UTC. Remove or comment 2 lines below if server clock time is in proper timezone
        d = datetime.datetime.today() + datetime.timedelta(days = -1)
        startdatetm = datetime.datetime.strftime(d,'%Y-%m-%d') + " 00:00:00"        

        d = datetime.datetime.today() + datetime.timedelta(days=1)
        enddatetm = datetime.datetime.strftime(d,'%Y-%m-%d') + " 08:00:00"

    if strategy.find('between') >= 0:
        # between separated by comma. 2nd element is start datetime and 3rd element is end datetime
        splitstrategy = strategy.split(",")

        # TBD: put validation here
        if splitstrategy[1]:
            startdatetm = splitstrategy[1].strip() # expected time here as well

        if splitstrategy[2]:
            enddatetm = splitstrategy[2].strip()
        
    dates = [startdatetm, enddatetm]
    
    return dates

# create db connection and fetch other config related data

driver = conn["driver"]
server = conn["server"]
database = conn["database"]
username = conn["username"]
password = conn["password"]

dbenv = "_test"
if env["prod"] == '1':
    dbenv = ""

maint_table = conn["maint_tablename"] + dbenv
release_tablename = conn["release_tablename"] + dbenv

try:
    cnxn = pyodbc.connect("Driver={"+ driver +"};"
                          "Server=" + server +";"
                          "Database="+ database +";"
                          "UID="+ username +";"
                          "PWD="+ password +";")
    cursor = cnxn.cursor()
    print ("Database Connected")
except Exception as e:
    print ("Error connecting Database",e)

try:

    # get the dates
    dates = gettimestrategy(mconfig["events_timestrategy"]["timerange"])
    resultset = {} #dictionary
    tempbody = ""

    # Query to get result from Maintenance
    query = "select apps_impacted, maint_type, maint_desc, environment, ticket, start_date_time \
         from "+ maint_table +" where start_date_time >='"+ dates[0]+"' and start_date_time <='"+ dates[1]+"'"
    
    cursor.execute(query)
    results = cursor.fetchall()
    if results:
        for rows in results:
            tempbody = tempbody + "<tr><th>" + rows[1] + "</th><th>" + rows[0] + "</th><th>" + rows[2] + "</th><th>" + rows[3] + "</th><th>" + rows[4] + "</th><th>" + datetime.datetime.strftime(rows[5], '%Y-%m-%d %H:%M:%S') + "</th></tr>"

    # Query to get result from Release
    query = "select rel_app_name, rel_dep_desc, rel_env, rel_chg_num, rel_dep_datetime \
         from "+ release_tablename +" where rel_dep_datetime >='"+ dates[0]+"' and rel_dep_datetime <='"+ dates[1]+"'"

    cursor.execute(query)
    results = cursor.fetchall()
    
    if results:
        for rows in results:
            tempbody = tempbody + "<tr><th>Change Request</th><th>" + rows[0] + "</th><th>" + rows[1] + "</th><th>" + rows[2] + "</th><th>" + rows[3] + "</th><th>" + datetime.datetime.strftime(rows[4], '%Y-%m-%d %H:%M:%S') + "</th></tr>"

    if len(tempbody) > 0:
            
        mailbody = """\
<html>
 <body>
  <table>
   <tr>
    <th>Event Type</th>
    <th>Application Name</th>
    <th>Description</th>
    <th>Environment</th>
    <th>Cherwell Ticket</th>
    <th>Start Date/Time</th>
   </tr>
"""           
        mailbody = mailbody + tempbody + """\
  </table>
 </body>
</html>
"""
        mailconf = mconfig["events_mail"]
        send_email(mailbody, mailconf["subject"], "", mailconf["recipient"])
        print ("Mail sent.. Exiting the application...")

except Exception as e:
  print ("An error occured...Please check...",e)

  
