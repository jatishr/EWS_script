# Description: This python script will insert data into Jira metrics table.
# Version: 1.0
# Date: 3/10/2021
# Author: Sushant Kumar
import subprocess
import datetime
import configparser
import pyodbc
import openpyxl
import re
import os
import sys

# pull the configuration file

mconfig = configparser.ConfigParser()
mconfig.read("jiradashboard.ini")

# create global variables
# initialize dictionary
mapping = mconfig["metrics_jira_mapping"]
monthstartend = mconfig["month_start_end"]
conn = mconfig["metricsdb"]
dept = ""
# Check if any argument has been passed.
# this script will run only when file in month-year.xlsx is provided.
if len(sys.argv) < 2:
  print ("Please provide the filename to parse. The file must be month and year number: e.g Jan-2021.xlsx")
  sys.exit(0)
else:
    # check if file is in xls or xlsx format
    filepath = sys.argv[1]
    filename_ext = os.path.basename(filepath) # filename with extension
    if not re.search('(xlsx|xls|xlsm)',filename_ext):
        print ("Provide correct excel file")
        sys.exit(0)

    # get the filename without extension to check the month
    filename = os.path.splitext(filename_ext)

    #split on " "; it should have two parts 1st one is month and second will be year
    spltfname = filename[0].split(" ")
    if len(spltfname) < 2:
        print ("The filename should be month year <department> e.g. Jan 2021 Development format")
        sys.exit(0)

    #check if first part is month and other part year
    f_month = spltfname[0].strip()
    f_month = f_month.lower()
    if  f_month not in monthstartend:
        print ("The filename should be Jan 2021 Development format")
        sys.exit(0)

    f_year = int(spltfname[1])
    if f_year < 2017:
        print ("The filename should be Jan 2021 Development format")
        sys.exit(0)

    #3122021- Sushant check if the filename shared have department
    # if yes then delete only department data else delete all month data
    if len(spltfname) == 3:
        dept = spltfname[2]

        # make is complete word if a person has input DEV or OPS
        if re.search(r'(DEV|DELV|DEVS)',dept, re.IGNORECASE):
            dept = "Development"
        elif re.search(r'OPS|OPERATION',dept, re.IGNORECASE):
            dept = "Operations"

  
# pull record from database
# input expected in the configuration: driver, server, database, username and password

def deletedata(cursor, startdate, enddate, department):
    # Daily Operations #3122021 - change query to reflect for which department data will be deleted
    if len(dept) > 0:
        sqlstmt = "select a.* from " +conn["tablename"] + " a \
                    INNER JOIN chtr_resources b ON b.res_chtr_userid = a.jira_username \
                    Where a.jira_work_date >= '" + startdate + "' and a.jira_work_date <= '" + enddate + "' \
                    AND b.res_department = '" + department +"'"
    else:
        sqlstmt = "select * from " +conn["tablename"] + " where jira_work_date >= '" + startdate + "' and jira_work_date <= '" + enddate + "'"

    print ("Executing delete statement: ", sqlstmt)
    
    try:
        cursor.execute(sqlstmt)
        results = cursor.fetchall()
        if results:
            if len(dept) > 0:
                sqlstmt = "delete a from " +conn["tablename"] + " a INNER JOIN chtr_resources b ON b.res_chtr_userid = a.jira_username where a.jira_work_date >= '" + startdate + "' and a.jira_work_date <= '" + enddate + "' AND b.res_department = '" + department +"'"
            else:
                sqlstmt = "delete from " +conn["tablename"] + " where jira_work_date >= '" + startdate + "' and jira_work_date <= '" + enddate + "'"
                
            cursor.execute(sqlstmt)
            cursor.commit()
            print ("Delete Completed....")

    except Exception as e:
        print ("Error while reading rows... ",e)
        sys.exit(0)

def insertdata(cursor, insertsql):
      
    try:
        cursor.execute(insertsql)
        cnxn.commit()

    except Exception as e:
        print ("Error while inserting data... ",e, insertsql)        

# this will be inserition program only. If a person is reloading same file then delete the data and insert the data
# create start date and end date
tempstartend = monthstartend[f_month].split(";")
startdate = str(f_year) + "-" + tempstartend[0] + "-" + tempstartend[1]
enddate = str(f_year) + "-" + tempstartend[0] + "-" + tempstartend[2]

# read excel file and build the insertion statement. It will be dictionary
wb = openpyxl.load_workbook(filepath)

sheet = wb['Worklogs']
row_count = sheet.max_row
i = 2 # initialize the row from data will be picked
insertstmt = {}
values = {}
for i in range (2, row_count + 1):
    values["jira_program"] = sheet[mapping["jira_program"] + str(i)].value

    #default value
    if values["jira_program"] is None:
        values["jira_program"] = "EWS"
        
    values["jira_issue_key"] = sheet[mapping["jira_issue_key"] + str(i)].value
    values["jira_issue_summary"] = sheet[mapping["jira_issue_summary"] + str(i)].value
    # escape single quotes is there is any
    if values["jira_issue_summary"] is None:
        values["jira_issue_summary"] = ""
    else:
        values["jira_issue_summary"] = values["jira_issue_summary"].replace("'","''")
    
    values["jira_work_date"] = sheet[mapping["jira_work_date"] + str(i)].value
    values["jira_username"] = sheet[mapping["jira_username"] + str(i)].value
    values["jira_account_key"] = sheet[mapping["jira_account_key"] + str(i)].value
    values["jira_account_name"] = sheet[mapping["jira_account_name"] + str(i)].value
    values["jira_component"] = sheet[mapping["jira_component"] + str(i)].value
    values["jira_all_components"] = sheet[mapping["jira_all_components"] + str(i)].value
    values["jira_version_name"] = sheet[mapping["jira_version_name"] + str(i)].value
    values["jira_issue_type"] = sheet[mapping["jira_issue_type"] + str(i)].value
    values["jira_issue_status"] = sheet[mapping["jira_issue_status"] + str(i)].value
    values["jira_project_key"] = sheet[mapping["jira_project_key"] + str(i)].value
    values["jira_project_name"] = sheet[mapping["jira_project_name"] + str(i)].value
    values["jira_epic"] = sheet[mapping["jira_epic"] + str(i)].value
    values["jira_epic_link"] = sheet[mapping["jira_epic_link"] + str(i)].value
    values["jira_work_description"] = sheet[mapping["jira_work_description"] + str(i)].value
    # escape single quotes is there is any
    if values["jira_work_description"] is None:
        values["jira_work_description"] = ""
    else:
        values["jira_work_description"] = values["jira_work_description"].replace("'","''")
    
    values["jira_parent_key"] = sheet[mapping["jira_parent_key"] + str(i)].value
    values["jira_reporter"] = sheet[mapping["jira_reporter"] + str(i)].value
    values["jira_billed_hours"] = sheet[mapping["jira_billed_hours"] + str(i)].value
    if len(str(values["jira_billed_hours"])) == 0:
        values["jira_billed_hours"] = 0
    
    values["jira_issue_orig_estm"] = sheet[mapping["jira_issue_orig_estm"] + str(i)].value

    if len(str(values["jira_issue_orig_estm"])) == 0:
        values["jira_issue_orig_estm"] = 0
        
    values["jira_issue_remain_estm"] = sheet[mapping["jira_issue_remain_estm"] + str(i)].value

    if len(str(values["jira_issue_remain_estm"])) == 0:
        values["jira_issue_remain_estm"] = 0

    #print (values["jira_billed_hours"], values["jira_issue_orig_estm"], values["jira_issue_remain_estm"])
    
    # create values
    sqlqval = ""
    sqlval= "" 
    for mapkey in mapping:
        sqlqval = sqlqval + mapkey + ","
        sqlval = sqlval + "'" + str(values[mapkey]) + "',"

    
    sqlstmt = "INSERT INTO "+ conn["tablename"]+ "(" + sqlqval[:-1]+ ") VALUES (" + sqlval[:-1] +")"
    insertstmt[i] = sqlstmt

# create db connection

driver = conn["driver"]
server = conn["server"]
database = conn["database"]
username = conn["username"]
password = conn["password"]

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



# check there is a record in the database; if yes then let us first delete it and then insert it
deletedata(cursor, startdate, enddate, dept)

print ("Starting insertion....")
# now insert
for k in insertstmt:
    print ("Inserting Record: ", k)
    insertdata(cursor, insertstmt[k])

print ("Program finished....")  
wb.close
                    
                
                
                
            
