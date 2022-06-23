# Description: This python script reads a csv file for upcoming EWS maintenances and insert data to EWS application database
# Version: 1.0
# Date: 11/16/2021
# Author: Kapil Narang

# Change Log
# 04/07/2022 - Implemented email function and program exit criteria


#*********************************************************************
#                   Imports
#*********************************************************************
import os
import sys
import csv
import pyodbc
import logging
import smtplib
import configparser

from datetime       import datetime
from email.message  import EmailMessage


#*********************************************************************
#                   Define IO and Logger files
#*********************************************************************

date = datetime.today().strftime('%Y-%m-%d')
in_file = 'ews_upcoming_events_' + date + '.csv'
log_file = 'ews_upcoming_events.log'

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Create file handler which logs even debug messages
fh = logging.FileHandler(log_file, mode='w')
fh.setLevel(logging.DEBUG)

# Create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

# Create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

ch.setFormatter(formatter)
fh.setFormatter(formatter)

# Add the handlers to logger
logger.addHandler(ch)
logger.addHandler(fh)


#*********************************************************************
#                   Import configuration file
#*********************************************************************

mconfig = configparser.ConfigParser()
mconfig.read("ews_upcoming_events_config.ini")


#*********************************************************************
#                   Function Definitions
#*********************************************************************

def insertdata(cursor, i_sql, index):
    try:    
      cursor.execute(i_sql)
      cnxn.commit()
    except pyodbc.IntegrityError:
        logger.info("Input data violates db integrity, check for duplicates. Row no:", index)
    except Exception as e:
        logger.info("Error executing insert : ",e, i_sql)


def sendemail():
    logger.info('Process complete.!!')

    #Parse email configuration details
    em_var = mconfig["ews_upcoming_events_email"]

    em_subject = em_var["subject"]
    em_sender = em_var["sender"]
    em_recipient = em_var["recipient"]
    em_server = em_var["emailserver"]
    em_body = em_var["body"]
    
    msg = EmailMessage()
    msg['Subject'] = em_subject
    msg['From'] = em_sender
    msg['To'] = em_recipient
    msg.set_content(em_body)

    if os.path.isfile(log_file):
        msg.add_attachment(open(log_file, "r").read(), filename=(log_file))

    s = smtplib.SMTP(em_server, 25)
    s.send_message(msg)
    s.quit()

    sys.exit()


#*********************************************************************
#                   Establish Database Connection
#*********************************************************************

#Parse DB configuration details
db_var = mconfig["ews_upcoming_events_db"]

driver = db_var["driver"]
server = db_var["server"]
database = db_var["database"]
username = db_var["username"]
password = db_var["password"]
table = db_var["tablename"]

try:
    cnxn = pyodbc.connect("Driver={"+ driver +"};"
                          "Server=" + server +";"
                          "Database="+ database +";"
                          "UID="+ username +";"
                          "PWD="+ password +";")
    cursor = cnxn.cursor()
    logger.info("Database Cconnection successful")
    
except Exception as e:
    logger.info("Error connecting Database",e)
    sendemail()

#*********************************************************************
#                   Variable Definition
#*********************************************************************

i_stmt_array = {}
cnt = 0
quote = '\''
comma = ','


#*********************************************************************
#                   Read input & create an insert sql array
#*********************************************************************
try:
    with open(in_file, 'r') as input_file:
        csv_reader = csv.reader(input_file)

        next(csv_reader)

        for row in csv_reader:
            cnt += 1
            apps_impacted = row[0]
            maint_type = row[1]
            maint_desc = row[2]
            environment = row[3]
            ticket = row[4]
            start_date_time = row[5]
            end_date_time = row[6]

            i_stmt = ('INSERT INTO '
                      + table
                      + ' VALUES ( '
                      + quote + apps_impacted + quote
                      + comma
                      + quote + maint_type + quote
                      + comma
                      + quote + maint_desc + quote
                      + comma
                      + quote + environment + quote
                      + comma
                      + quote + ticket + quote
                      + comma
                      + quote + start_date_time + quote
                      + comma
                      + quote + end_date_time + quote
                      + ');')

            i_stmt_array[cnt] = i_stmt
            
except FileNotFoundError:
    logger.info(in_file + " file not found")
    sendemail()
except IOError:
    logger.info("Error reading input file")
    sendemail()


#*********************************************************************
#                   Insert data to database
#*********************************************************************

logger.info("Initiating data load.!!")
for i in i_stmt_array:
    logger.info("Inserting Record: %d" % (i))
    insertdata(cursor, i_stmt_array[i], i)


#*********************************************************************
#                   Delete input file after data ingestion
#*********************************************************************

if os.path.exists(in_file):
  os.remove(in_file)
  logger.info("Input file deleted.")
else:
  logger.info("Error deleting the file. Delete manually.")


sendemail()
#*********************************************************************
#                   End of Program
#*********************************************************************
