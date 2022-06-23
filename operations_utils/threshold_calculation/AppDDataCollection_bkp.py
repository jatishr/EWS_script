# This python script will pull data from AppD 
# Phase 1 - pull data and then place in text file to be parsed
# Version - 1.0
# Date - 6/1/2020
# Author - Sushant Kumar

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import json
import subprocess
from xml.etree import ElementTree
import datetime
import configparser
import pyodbc
import urllib.parse
import time

# Parse the config file to get appdynamics token
tconfig = configparser.ConfigParser()
tconfig.read('threshold.ini')

driver = tconfig["dbconfig"]["driver"]
server = tconfig["dbconfig"]["server"]
database = tconfig["dbconfig"]["database"]
username = tconfig["dbconfig"]["username"]
password= tconfig["dbconfig"]["password"]

# 2/26/2021 - Write in logs open file
fh = open("appd_raw_data_collection.log","a")

def logappend(text):
    fh.write(text +"\n")

logappend("Program Started: " + str(datetime.datetime.today()))

try:
    cnxn = pyodbc.connect("Driver={"+ driver +"};"
                          "Server=" + server +";"
                          "Database="+ database +";"
                          "UID="+ username +";"
                          "PWD="+ password +";")
    cursor = cnxn.cursor()
    print ("Database Connected")
    logappend("Database Connected")
except Exception as e:
    print ("Error connecting Database",e)
    logappend("Database Connected " + e)

# function to generate the authentication bearer/token
# the token or bearer is only live for 5 min
# it will take token information and return dictionary authentication and time
def generateauthtoken(tconfig):
    # the threshold value configuration
    

    token_url = tconfig["appdconfig"]["tokenurl"]
    client_id = tconfig["appdconfig"]["clientid"]
    client_secret = tconfig["appdconfig"]["clientsecret"]
    
    headers = {"Content-Type": "application/vnd.appd.cntrl+protobuf;v=1", "cache-control": "no-cache" }
    payload = "grant_type=client_credentials&client_id="+client_id+"&client_secret=" + client_secret

    # insecure request warning to supress certs error
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    access_token_response = requests.post(token_url, data=payload, headers=headers, verify=False, allow_redirects=False)

    #print (access_token_response.headers)

    # return should be in token and time
    retauthtoken = dict() 

    # check if text is returned
    if access_token_response.text:
        try:
            #print (access_token_response.text)

            tokens = json.loads(access_token_response.text)

            #print ("access token:" + tokens['access_token'])
            retauthtoken["access_token"] = tokens['access_token']
            retauthtoken["exp_time"] = tokens['expires_in']

        except Exception as e:
            print ("No token returned", e)
            logappend("No token returned "+ e)

    return retauthtoken

# function to fetch appd data colletion type
def appddatacol():

    sqlstr = "select datacol_name from appd_metric_datacol_type"
    cursor.execute(sqlstr)
    datacolrow = cursor.fetchall()
    return datacolrow

# function to convert in miliseconds
def convmilisesconds(dttm):
    convmilsecdttm = datetime.datetime.strptime(dttm,'%Y-%m-%d %H:%M:%S')
    convmilsecdttm =  int(convmilsecdttm.timestamp() * 1000)
    return convmilsecdttm

# strategy 
def gettimestrategy(strategy):
    #return start date and end date
    dates = []
    currentdatetm = datetime.datetime.today()
    startdatetm = str(currentdatetm.date()) + " 00:00:00"

    # find will give negative if no data found
    if strategy.find('today') >= 0:
        startdatetm = str(currentdatetm.date()) + " 00:00:00"
        enddatetm = str(currentdatetm.date()) +" " + str(currentdatetm.hour) + ":00:00"

    # 2/26/2021 - Sushant Added Yesterday clause where data will be pulled one day before
    if strategy.find('yesterday') >= 0:
        d = datetime.datetime.today() + datetime.timedelta(days = -1)
        startdatetm = datetime.datetime.strftime(d,'%Y-%m-%d') + " 00:00:00"
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

# function to insert or update the data
def insertupdatedb(dbdata, tm, value):

    # check if program, application, environment,tm is there or not. if yes
    # then update the value else insert the value
    program = dbdata[0]
    application = dbdata[1]
    env = dbdata[2]
    datacol = dbdata[3]
    reptype = dbdata[4]

    sqlstr = "select * from dbo.appd_metric_data_raw \
WHERE raw_program ='" + program + "' \
AND raw_appdapplication ='" + application + "' \
AND raw_datacol_name = '" + datacol +"' \
AND raw_env = '" + env +"' \
AND raw_overall_servicename ='" + reptype +"' \
AND raw_datetime = '" + tm + "'"
    cursor.execute(sqlstr)
    results = cursor.fetchall()
    if len(results):
        updinsqlstr = "update dbo.appd_metric_data_raw set raw_observed_data = '" + str(value) + "' \
        WHERE raw_program ='" + program + "' \
        AND raw_appdapplication ='" + application + "' \
        AND raw_datacol_name = '" + datacol +"' \
        AND raw_env = '" + env + "' \
        AND raw_overall_servicename ='" + reptype +"' \
        AND raw_datetime = '" + tm + "'"
    else:
        updinsqlstr = "insert into dbo.appd_metric_data_raw (raw_program, raw_appdapplication, raw_datacol_name, raw_env, raw_overall_servicename, \
raw_datetime, raw_observed_data) values ('"+ program +"', '" + application + "', '" + datacol +"', '" + env +"', '" + reptype +"','" + tm +"', '" + str(value) +"')"

    try:
        cursor.execute(updinsqlstr)
        cnxn.commit()
    except Exception as e:
        print ("Error Updating/Inserting data",e)
        logappend("Error Updating/Inserting data " + e)

# function to pull raw data from appd
# input dataconfig and appd server config
def getpullappdrawdata(appconfig, dataconfig, tconfig, dbdata ):

    # check what is the time stragegy need to implement
    # if no time then hourly will consdered
    # initialize the start date time with the midnight of a day
    # initialize the end datetime with the top of -1 hour 
    currentdatetm = datetime.datetime.today()
    startdatetm = str(currentdatetm.date()) + " 00:00:00"
    enddatetm = str(currentdatetm.date()) +" " + str(currentdatetm.hour) + ":00:00"
    dates = gettimestrategy(appconfig["PROD-TimeStrategy"]["timerange"])
    # check the strategy
    if dates:
        startdatetm = dates[0]
        enddatetm = dates[1]

    startdtm_milsecs = convmilisesconds(startdatetm)
    enddatetm_milsecs = convmilisesconds(enddatetm)

    # initialize autherization time limit
    # 9/1/2020 - Sushant Ensure inflight request is not failing so say after timecheck the token crosses 300 sec it will fail.
    # wanted to give sufficient time
    authtime = 290
    # get bearer
    # the time limit of bearer is 300sec which is 5 min. we have to keep counter of it
    rettoken = generateauthtoken(tconfig)
    bearer = ""
    if rettoken:
        bearer = str(rettoken["access_token"])
        authtime = int(rettoken["exp_time"])

    # check point to ensure if time is exceeding new bearer can be pulled
    checkpointtime = currentdatetm + datetime.timedelta(seconds=authtime)
    
    #print (startdatetm, enddatetm)
    for reptype in appconfig[datacolconfig]:
        # 7/16/2020: Sushant Check if bearer time has completed or not else generate new one.
        if datetime.datetime.today() >= checkpointtime:
            # generate new one
            rettoken = generateauthtoken(tconfig)
            bearer = ""
            if rettoken:
                bearer = str(rettoken["access_token"])
                authtime = int(rettoken["exp_time"])
                checkpointtime = datetime.datetime.today() + datetime.timedelta(seconds=authtime)
            
        
        url = appconfig[datacolconfig][reptype]
        #url = urllib.parse.unquote(url)
        # Replace START_MILLISECONDS and END_MILISECONDS with time
        url = url.replace("<START_MILISECONDS>",str(startdtm_milsecs))
        url = url.replace("<END_MILISECONDS>",str(enddatetm_milsecs))
        
        print (reptype,url)

        # 7/16/2020 we have to pop the last element of dbdata so the 5th element will be reptype
        if len(dbdata) == 5:
            dbdata.pop()

        dbdata.append(reptype)
        
        # we have now url so better to start running the data and pulling data
        metricheaders = {
            "Content-Type": "application/xml",
            "Authorization": "Bearer " + bearer,
            "cache-control": "no-cache"
            }

        # 7/17/2020 - try and catch exception 
        try:
            res = requests.get(url, headers=metricheaders, verify=False, allow_redirects=False)
            print (res.headers, res.text)
            
        except Exception as e:
            print ("Error occured..... ", e)
            continue
            

        # response is in xml format
        tree = ElementTree.fromstring(res.content)
        tm = ''
        value = 0

        #7/16/2020 - Close the response once work is done
        res.close()
        for child in tree.iter():
            if child.tag == "startTimeInMillis":
                tm = datetime.datetime.fromtimestamp(int(child.text)/1000.0).strftime('%Y-%m-%d %H:%M:%S')
                print (child.tag, tm)
            elif (child.tag == "value"):
                value = int(child.text)
                print (child.tag, child.text)

            #insert data in the table
            if value:
                # Call function to add or update data
                # values that are passed is connection cursor, program data, time and value
                insertupdatedb(dbdata, tm, value)
                # reset the value
                tm = ''
                value = 0
        
    return 1


# get the program and project configuration
# check for which all program and project is ready for query
pconfig = configparser.ConfigParser()
pconfig.read("program_project.ini")

#get data col
datacolrow = appddatacol()

# loop it program and then project
for prg in pconfig["program"]:
    prgname = prg.upper()
    print (prgname)
    logappend(prgname)

    #check if program is reguired to parse of not
    if pconfig["program"][prgname] == '1':

        #fetch application name
        tempappname = prgname.upper() +"_Application"
        print (tempappname)
        logappend(tempappname)

        #Check if program application exists then pull all applicaitons of program and through it
        if tempappname not in pconfig:
            continue
        else:
            #get applicaiton name
            for appl in pconfig[tempappname]:
                if pconfig[tempappname][appl.upper()] == '1':
                    print (appl)
                    logappend(appl)

                    # now the application name should have same ini file as well
                    # open the config file and look for environment
                    # loop in each environment and metric category
                    appfilename = appl + ".ini"
                    appconfig = configparser.ConfigParser()
                    appconfig.read(appfilename)

                    # now check for each environment and data collection
                    for env in appconfig['environment']:
                        print (env.upper())
                        logappend(env.upper())
                        if appconfig['environment'][env.upper()] == '1':
                            # now run through data collection with env
                            for row in datacolrow:
                                datacolconfig = env.upper() + "-" + row[0]
                                print (datacolconfig)
                                logappend(datacolconfig)
                                if appconfig[datacolconfig]:
                                    # fetch data from the application
                                    #Supply program, application, environment info)
                                    dbdata = [prgname, appl.upper(), env.upper(), row[0] ]
                                    ret = getpullappdrawdata(appconfig, datacolconfig, tconfig, dbdata)

                                    #7/16/2020 - Sleep in between to give more breathing time and reset the connections
                                    time.sleep(10)

#2/26/2021 - Close the file after function is over
fh.close
                                        
                            
                    
        

