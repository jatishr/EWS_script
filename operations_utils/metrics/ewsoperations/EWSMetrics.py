# Description: This python script will pull data from different sources and create performance report
# Version: 1.0
# Date: 1/11/2021
# version: 2.0
# Date: 3/16/2021
# Description: Pull data from different database and update excel sheet
# Version: 3.0
# Description: Support different time settings, save template as weekly report; send mail
# Author: Sushant Kumar
import subprocess
import datetime
import time
import configparser
import pyodbc
import openpyxl
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

# pull the configuration file

mconfig = configparser.ConfigParser()
mconfig.read("metrics.ini")

# create global variables
# initialize dictionary
programs = mconfig["program"]
resources = {}

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

    msg.attach(MIMEText(body, 'plain'))

    # Open a file in binary mode
    with open(filename, "rb") as attachment:
        # Add file as application/octet-stream
        # Email client can usually download this automatically as attachment
        part = MIMEBase("application","octet-stream")
        part.set_payload(attachment.read())

    # Encode file in ASCII characters to send by email  
    encoders.encode_base64(part)

    # Add attachment to message and convert message to string
    part.add_header(
        "Content-Disposition",
        f"attachment; filename= {filename}",
    )

    msg.attach(part)
    text = msg.as_string()
    
    s = smtplib.SMTP('mailrelay.chartercom.com', 25)
    s.starttls()   
    text = msg.as_string()
    s.sendmail(fromaddr, recipient, text)
    s.quit()

# 8/19/2021 timestrategy strategy 
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
        d = datetime.datetime.today() + datetime.timedelta(days = -7)
        startdatetm = datetime.datetime.strftime(d,'%Y-%m-%d') + " 00:00:00"
        enddatetm = datetime.datetime.strftime(d,'%Y-%m-%d') + " 23:59:59"

    if strategy.find('yeartodate') >= 0:
        #check the year and start time will be start of the year
        d = datetime.datetime.today() + datetime.timedelta(days = -7)
        startdatetm = str(d.year) + "-01-01" + " 00:00:00"
        # since timer will run on monday we will take last week's saturday into account
        d = datetime.datetime.today() + datetime.timedelta(days = -2)
        enddatetm = datetime.datetime.strftime(d,'%Y-%m-%d') + " 23:59:59"

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

# function to have correct name
# if not found correct then return correct name
def resnamecorr(resname):
    resnamedict = mconfig["ews-ops_resource"]
    # split the input and check first and last name
    splitnm = resname.split(" ")

    #check if resname exists or not
    if resname not in resnamedict:
        # run down each key and search name similarity
        for nm in resnamedict:
            if splitnm[0].upper() in nm.upper():
                resname = nm                
                
    return resname
    

# pull record from database
# input expected in the configuration: driver, server, database, username and password
def connectionsdb(conn):
    driver = mconfig[conn]["driver"]
    server = mconfig[conn]["server"]
    database = mconfig[conn]["database"]
    username = mconfig[conn]["username"]
    password = mconfig[conn]["password"]

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

    # get the record counter and build a dictionary
    rowcnt = 1

    for ds in mconfig[conn + "_datasources"]:

        # now we have dsheader and see what sql statment it has
        if mconfig[conn + "_datasources"][ds] == "1":

            if ds in mconfig["sqlstmt"]:

                sqlstmt = mconfig["sqlstmt"][ds]
                # now update start date and end date with the config value
                # 8/19/2021 - Change in the way date is being called
                dates = gettimestrategy(mconfig["dates"]["timerange"])
                #startdate = mconfig["dates"]["fromdate"]
                #enddate = mconfig["dates"]["enddate"]
                #sqlstmt = sqlstmt.replace("?STARTDATE",startdate)
                #sqlstmt = sqlstmt.replace("?ENDDATE",enddate)

                sqlstmt = sqlstmt.replace("?STARTDATE",dates[0])
                sqlstmt = sqlstmt.replace("?ENDDATE", dates[1])


                print ("Executing SQLSTMT: ", sqlstmt)
   
                try:
                    cursor.execute(sqlstmt)
                    results = cursor.fetchall()

                    # Rows expected:
                    # 0=Resource Name 1=Date 2=Operations Category 3=Status 4=Hours Spent 5=Ticket Number if any  6=Work Description  7=Application 8=Program 9=Source
 
                    for row in results:

                        # get the date from the row[resolition datetm]
                        resdt = '1900-01-01'
                        if row[1] and datetime.datetime.strftime(row[1],'%Y-%m-%d') != resdt:
                            resdt = datetime.datetime.strftime(row[1],'%Y-%m-%d')
                        elif row[9] == "Daily Operations" and row[10]:
                            resdt = datetime.datetime.strftime(row[10],'%Y-%m-%d')

                        # 8/16/2021 - Removing dependencies of resources
                        resources[rowcnt] = dict()
                        resources[rowcnt]["Resources"] = row[0]
                        
                        resources[rowcnt]["Date"] = resdt
                        
                        if row[2]:
                            resources[rowcnt]["Operations_Category"] = row[2].upper()
                        else:
                            resources[rowcnt]["Operations_Category"] = row[2]

                        if row[3]:
                            resources[rowcnt]["Status"] = row[3].upper()
                        else:
                            resources[rowcnt]["Status"] = row[3]
                                
                        if row[4]:    
                            resources[rowcnt]["Hours_Spent"] = round(float(row[4]) / 60,2)
                        else:
                            resources[rowcnt]["Hours_Spent"] = float(0)
                                
                        resources[rowcnt]["Ticket"] = row[5]
                        resources[rowcnt]["Work_Description"] = row[6]

                        if row[7]:
                            resources[rowcnt]["Application"] = row[7].upper()
                        else:
                            resources[rowcnt]["Application"] = row[7]
                                
                        resources[rowcnt]["Program"] = row[8]
                        resources[rowcnt]["Source"] = row[9]

                        # 8/19/2021 - Sushant year and week number to be added to the excel 
                        dt = datetime.datetime.strptime(resdt,"%Y-%m-%d")
                        resources[rowcnt]["Year"] = dt.year
                        weeknum = datetime.datetime.strftime(dt,'%W')
                        if weeknum == '00':
                            weeknum = 1
                            
                        resources[rowcnt]["WeekNum"] = int(weeknum)

                        rowcnt = rowcnt + 1

                except Exception as e:
                    print ("Error while reading rows... ",e)


    return resources
                
# determine what type of connection is there and how to pull data from downstream
def connectionsdata(conn):
    # from the parsed variable check the connection configuration
    connconfig = mconfig[conn]

    # each connection we expect "type" key word so results can be pulled accordingly
    if mconfig[conn]["type"] == "db":
        resources = connectionsdb(conn)

    return resources

# 8/19/2021 - Sushant save the template file first and save it as current datetime
curdttm = datetime.datetime.strftime(datetime.datetime.now(),'%Y%m%d%H%M%S')
if os.path.exists("Metrics_Template.xlsx"):
    os.popen('copy Metrics_Template.xlsx Metrics_'+curdttm+'.xlsx')
    time.sleep(10)

# open the excel sheet where we have to update the counts
if os.path.exists('Metrics_'+curdttm+'.xlsx'):
    filepath = 'Metrics_'+curdttm+'.xlsx'
else:
    filepath = 'Metrics_Template.xlsx'
# read excel file 
wb = openpyxl.load_workbook(filepath)

sheet = wb['WorkLogs']
# 8/19/2021 -Sushant No need to delete. Template file will be fresh
#row_cnt = sheet.max_row
# delete all rows if there is any data there
#sheet.delete_rows(2, row_cnt)

# get the date rows
row_cnt = 1

for prg in programs:
    # Check if we are going to run the report of progam 1 = Yes 0 = No
    if programs[prg] == '1':

        # Run through the connections from where we have to pull the records
        conntext = prg + "-connections"
        for conn in mconfig[conntext]:
            # Check if the connection is 1 or 0. 1 means green light to parse data; 0 means ignore it
            if mconfig[conntext][conn] == '1':
                #function to parse the data
                resources = connectionsdata(conn)
                #print (resources)

                #Now we have name, we have to update those to the sheet
                
                for res in resources:
                    
                    #print (res,"\t",sorted(resources[res].items()))
                    row_cnt = row_cnt + 1
                    sheet["A" + str(row_cnt)].value = resources[res]["Resources"]
                    sheet["B" + str(row_cnt)].value = datetime.datetime.strptime(resources[res]["Date"],'%Y-%m-%d')
                    sheet["C" + str(row_cnt)].value = resources[res]["Operations_Category"]
                    sheet["D" + str(row_cnt)].value = resources[res]["Status"]
                    sheet["E" + str(row_cnt)].value = resources[res]["Hours_Spent"]
                    sheet["F" + str(row_cnt)].value = resources[res]["Ticket"]
                    sheet["G" + str(row_cnt)].value = resources[res]["Work_Description"]
                    sheet["H" + str(row_cnt)].value = resources[res]["Application"]
                    sheet["I" + str(row_cnt)].value = resources[res]["Program"]
                    sheet["J" + str(row_cnt)].value = resources[res]["Source"]
                    # 8/19/2021 - Sushant year and week number to be added to the excel
                    sheet["K" + str(row_cnt)].value = resources[res]["Year"]
                    sheet["L" + str(row_cnt)].value = resources[res]["WeekNum"]

wb.save(filepath)
wb.close

# 8/19/2021 - Now since data has been published in the excel sheet. Let us mail to individuals
print ("Metrics Sheet completed. Sending mail....")
maildetails = mconfig["mail"]
send_email(maildetails["body"],maildetails["subject"],filepath, maildetails["recipient"])

print ("Program Completed...")                    
                
                
                
            
