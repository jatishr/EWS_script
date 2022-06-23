# This python script will pull data from database and calculate  
# percentile and standard deviation
# Version - 1.0
# Date - 6/15/2020
# Author - Sushant Kumar

import subprocess
import datetime
import configparser
import pyodbc
import numpy as np
import statistics
import os

# Parse the config file to get appdynamics token
# 5/26/2021 - Set the path of config file
rootpath = os.getcwd()
# change to get config path
os.chdir("../config/")
configpath = os.getcwd() + "/"

tconfig = configparser.ConfigParser()
tconfig.read(configpath + 'threshold.ini')

# change back to original path so logs can be written
os.chdir(rootpath)

driver = tconfig["dbconfig"]["driver"]
server = tconfig["dbconfig"]["server"]
database = tconfig["dbconfig"]["database"]
username = tconfig["dbconfig"]["username"]
password= tconfig["dbconfig"]["password"]

# Open database connection
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

    currentdatetm = datetime.datetime.today() + datetime.timedelta(days = -1 )
    startdatetm = str(currentdatetm.date()) 
    enddatetm = str(currentdatetm.date()) 

    if strategy == "today":
        dates = [startdatetm, enddatetm]

    if strategy.find('between') >= 0:

    # between separated by comma. 2nd element is start datetime and 3rd element is end datetime
        splitstrategy = strategy.split(",")

        # TBD: put validation here
        if splitstrategy[1]:
            startdatetm = splitstrategy[1].strip()[0:10] # expected time here as well

        if splitstrategy[2]:
            enddatetm = splitstrategy[2].strip()[0:10]

        dates = [startdatetm, enddatetm]

    return dates

# function to insert or update the data
def insertupdatedb(percstdval):

    # check if program, application, environment,tm is there or not. if yes
    # then update the value else insert the value
    # dtval EWS|SPC|ErrorPerMin|PROD|overall|2020-01-31
    # program|application|datacollection|enviornment|report type|date
    # percstdval is a two dimentional dictionary

    for p,v in percstdval.items():

        splitdtval = p.split("|")
    
        program = splitdtval[0]
        application = splitdtval[1]
        datacol = splitdtval[2]
        env = splitdtval[3]
        reptype = splitdtval[4]
        dt = splitdtval[5]

        # now v is dictionary to capture the percentile and standard value

        #7/18/2020 initialize variables
        perc99 = perc95 = perc90 = perc75 = perc50 = perc25 = stdv99 = stdv95 = stdv90 = stdv75 = stdv50 = stdv25 = 0

        try:
            perc99 = v["perc99"]
            perc95 = v["perc95"]
            perc90 = v["perc90"]
            perc75 = v["perc75"]
            perc50 = v["perc50"]
            perc25 = v["perc25"]

            stdv99 = v["stdv99"]
            stdv95 = v["stdv95"]
            stdv90 = v["stdv90"]
            stdv75 = v["stdv75"]
            stdv50 = v["stdv50"]
            stdv25 = v["stdv25"]
        except Exception as e:
            print ("Error occured: ", e)
            pass
            
        sqlstr = "select * from dbo.appd_metric_perc_std_monthly \
    WHERE perc_std_m_program ='" + program + "' \
    AND perc_std_m_appdapplication ='" + application + "' \
    AND perc_std_m_datacol_name = '" + datacol +"' \
    AND perc_std_m_env = '" + env +"' \
    AND perc_std_m_overall_servicename ='" + reptype +"' \
    AND perc_std_m_monthyear = '" + dt + "'"
        cursor.execute(sqlstr)
        results = cursor.fetchall()
        if len(results):
            updinsqlstr = "update dbo.appd_metric_perc_std_monthly set perc_m_99 = '" + str(perc99) + "',  \
            perc_m_95 = '" + str(perc95) + "', perc_m_90 = '" + str(perc90) +"', perc_m_75 = '" + str(perc75) +"', perc_m_50 = '" + str(perc50) +"', perc_m_25 = '" + str(perc25) +"', \
            std_m_99 ='" + str(stdv99) + "', std_m_95 = '" + str(stdv95) + "', std_m_90 = '" + str(stdv90) +"', std_m_75 = '" + str(stdv75) +"', std_m_50 = '" + str(stdv50) +"', std_m_25 = '" + str(stdv25) +"' \
            WHERE perc_std_m_program ='" + program + "' \
            AND perc_std_m_appdapplication ='" + application + "' \
            AND perc_std_m_datacol_name = '" + datacol +"' \
            AND perc_std_m_env = '" + env + "' \
            AND perc_std_m_overall_servicename ='" + reptype +"' \
            AND perc_std_m_monthyear = '" + dt + "'"
        else:
            updinsqlstr = "insert into dbo.appd_metric_perc_std_monthly (perc_std_m_program, perc_std_m_appdapplication, perc_std_m_datacol_name, perc_std_m_env, perc_std_m_overall_servicename, \
    perc_std_m_monthyear, perc_m_99, perc_m_95, perc_m_90, perc_m_75, perc_m_50, perc_m_25, std_m_99, std_m_95, std_m_90, std_m_75, std_m_50, std_m_25) values \
    ('"+ program +"', '" + application + "', '" + datacol +"', '" + env +"', '" + reptype +"','" + dt +"', '" + str(perc99) +"', \
    '" + str(perc95) +"', '" + str(perc90) +"', '" + str(perc75) +"', '" + str(perc50) +"', '" + str(perc25) +"', \
    '" + str(stdv99) +"', '" + str(stdv90) +"', '" + str(stdv95) +"', '" + str(stdv75) +"', '" + str(stdv50) +"', '" + str(stdv25) +"')"

        try:
            cursor.execute(updinsqlstr)
            cnxn.commit()
        except Exception as e:
            print ("Error Updating/Inserting data",e, updinsqlstr)

# function to pull raw data from appd
# input dataconfig and appd server config
def getpullappdrawdata(appconfig, dataconfig, tconfig, dbdata ):

    # check what is the time stragegy need to implement
    # if no time then one day before should be taken into consideration
    # initialize the start date time with the midnight of a day
    # initialize the end datetime with the bottom of 11 PM
    currentdatetm = datetime.datetime.today() + datetime.timedelta(days = -1 )
    startdatetm = str(currentdatetm.date())
    enddatetm = str(currentdatetm.date()) 
    dates = gettimestrategy(appconfig["PROD-TimeStrategy"]["timerange"])
    # check the strategy
    if dates:
        startdatetm = dates[0]
        enddatetm = dates[1]

    # Now run the query between dates. Create dictionary for each date. hold list of data for each dictionary
    sqlstmt = "select perc_std_d_program, perc_std_d_appdapplication, perc_std_d_datacol_name, perc_std_d_env, perc_std_d_overall_servicename, perc_std_d_date, \
perc_d_99, perc_d_95, perc_d_90, perc_d_75, perc_d_50, perc_d_25 \
FROM dbo.appd_metric_perc_std_daily where perc_std_d_date between '" + startdatetm + "' and '" + enddatetm +"' \
AND perc_std_d_program = '" + dbdata[0] +"' \
AND perc_std_d_appdapplication = '"+ dbdata[1] +"' \
AND perc_std_d_env = '" + dbdata[2] +"' \
AND perc_std_d_datacol_name ='" + dbdata[3] +"'"
    
    cursor.execute(sqlstmt)
    rawrows = cursor.fetchall()

    # initialize a dictionary
    rawtimedict = {}
    
    for row in rawrows:

        # for each row get percentile value the order of percentile variable should be same as row column fetched.
        # position 6 in the query is perc_d_99 and 11th is perc_d_25
        for i in range (6, 12):
        
            # create a unique string using rows else we have to put lots of dictionary
            rowstr  = row[0] + "|" + row[1] + "|" +row[2] + "|" + row[3] + "|" + row[4] + "|" + str(datetime.datetime.strftime(row[5],'%b-%Y')) + "|" + str(i)
            
            if rowstr not in rawtimedict:
                #initialize
                rawtimedict[rowstr] = []
                
            rawtimedict[rowstr].append(int(row[i]))

    # Capture the calculation result
    percstdval = {}
    # now run loop to print the value
    for dt,val in rawtimedict.items():
        try:
            print (dt)
            # split dt the last digit will signifies percentile
            splitdt = dt.split("|")

            tempdt = splitdt[0] + "|" + splitdt[1] + "|" +splitdt[2] + "|" + splitdt[3] + "|" + splitdt[4] + "|" + splitdt[5]

            if tempdt not in percstdval:
                percstdval[tempdt] = dict()
                
            if splitdt[6] == "6":
                perc99 = int(np.percentile(val,99))
                stdv99 = round(statistics.stdev(val),3)
                
                percstdval[tempdt]["perc99"] = perc99
                percstdval[tempdt]["stdv99"] = stdv99
                
                print ("99", perc99)
                print ("Standard Deviation:", stdv99)
                

            if splitdt[6] == "7":
                perc95 = int(np.percentile(val,95))
                stdv95 = round(statistics.stdev(val),3)
                
                print ("95", perc95)
                print ("Standard Deviation:", stdv95)
                
                percstdval[tempdt]["perc95"] = perc95
                percstdval[tempdt]["stdv95"] = stdv95

            if splitdt[6] == "8":
                perc90 = int(np.percentile(val,90))
                stdv90 = round(statistics.stdev(val),3)
                print ("90", perc90)
                print ("Standard Deviation:", stdv90)
                
                percstdval[tempdt]["perc90"] = perc90
                percstdval[tempdt]["stdv90"] = stdv90


            if splitdt[6] == "9":
                perc75 = int(np.percentile(val,75))
                stdv75 = round(statistics.stdev(val),3)
                print ("75", perc75)
                print ("Standard Deviation:", stdv75)

                percstdval[tempdt]["perc75"] = perc75
                percstdval[tempdt]["stdv75"] = stdv75

                
            if splitdt[6] == "10":
                perc50 = int(np.percentile(val,50))
                stdv50 = round(statistics.stdev(val),3)
                print ("50", perc50)
                print ("Standard Deviation:", stdv50)
                
                percstdval[tempdt]["perc50"] = perc50
                percstdval[tempdt]["stdv50"] = stdv50

            if splitdt[6] == "11":
                perc25 = int(np.percentile(val,25))
                stdv25 = round(statistics.stdev(val),3)
                print ("25", perc25)
                print ("Standard Deviation:", stdv25)

                percstdval[tempdt]["perc25"] = perc25
                percstdval[tempdt]["stdv25"] = stdv25

        except Exception as e:
            print ("Error occured...", e)
            pass

            
    #insert or update this value
    insertupdatedb(percstdval)

    return 1

# get the program and project configuration
# check for which all program and project is ready for query
pconfig = configparser.ConfigParser()
pconfig.read(configpath + "program_project.ini")

#get data col
datacolrow = appddatacol()

# loop it program and then project
for prg in pconfig["program"]:
    prgname = prg.upper()
    print (prgname)

    #check if program is reguired to parse of not
    if pconfig["program"][prgname] == '1':

        #fetch application name
        tempappname = prgname.upper() +"_Application"
        print (tempappname)

        #Check if program application exists then pull all applicaitons of program and through it
        if tempappname not in pconfig:
            continue
        else:
            #get applicaiton name
            for appl in pconfig[tempappname]:
                if pconfig[tempappname][appl.upper()] == '1':
                    print (appl)

                    # now the application name should have same ini file as well
                    # open the config file and look for environment
                    # loop in each environment and metric category
                    appfilename = appl + ".ini"
                    appconfig = configparser.ConfigParser()
                    appconfig.read(configpath+appfilename)

                    # now check for each environment and data collection
                    for env in appconfig['environment']:
                        print (env.upper())
                        if appconfig['environment'][env.upper()] == '1':
                            # now run through data collection with env
                            for row in datacolrow:
                                datacolconfig = env.upper() + "-" + row[0]
                                print (datacolconfig)
                                if appconfig[datacolconfig]:
                                    # fetch data from the application
                                    #Supply program, application, environment info)
                                    dbdata = [prgname, appl.upper(), env.upper(), row[0] ]
                                    ret = getpullappdrawdata(appconfig, datacolconfig, tconfig, dbdata)
                                    
                                        
                            
                    
        

