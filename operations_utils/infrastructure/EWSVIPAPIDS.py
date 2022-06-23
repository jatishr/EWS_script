# Description: This python script will insert/update data into vip_api_datasource.
# Version: 1.0
# Date: 6/11/2021
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
mconfig.read("EWSVIPAPIDS.ini")

# create global variables
# initialize dictionary
vipapids_detail_mapping = mconfig["vipapids_mapping"]
conn = mconfig["vipapidsdb"]
dept = ""
# Check if any argument has been passed.
if len(sys.argv) < 2:
  print ("Please provide the filename to parse. To parse onboading form please mention ticket number")
  sys.exit(0)
else:
    # check if file is in xls or xlsx format
    filepath = sys.argv[1]
    filename_ext = os.path.basename(filepath) # filename with extension
    if not re.search('(xlsx|xls|xlsm)',filename_ext):
        print ("Provide correct excel file")
        sys.exit(0)

def fetchkeyval (cursor, hostval, portval, typeval):

  flag = 0
  try:
    sqlstmt = "SELECT TOP 1 * FROM " + conn["tablename"] + " WHERE vip_api_ds_hostname = '" + hostval + "' and vip_api_ds_port ='" + str(portval) +"' \
                and vip_api_ds_type='" + typeval + "'"
    cursor.execute(sqlstmt)
    results = cursor.fetchall()
    if results:
      flag = 1

    return flag    

  except Exception as e:
    return 1

def insertupdatedata(cursor, insertsql):
      
    try:    
      cursor.execute(insertsql)
      cnxn.commit()

    except Exception as e:
        print ("Error while inserting/Updating data... ",e, insertsql)        

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

# read excel file and build the insertion statement. It will be dictionary
wb = openpyxl.load_workbook(filepath)

# check what we have parse;
# form or details. 
sheet = wb['VIPAPIDataSource']
  
row_count = sheet.max_row
i = 2 # initialize the row from data will be picked
insertupdatestmt = {}
values = {}

for i in range (2, row_count + 1): # the onboarding details to run each row and create insert/update  

  if not sheet[vipapids_detail_mapping["vip_api_ds_hostname"] + str(i)].value:
    break
    
  values["vip_api_ds_hostname"] = sheet[vipapids_detail_mapping["vip_api_ds_hostname"] + str(i)].value    
  values["vip_api_ds_ips"] = str(sheet[vipapids_detail_mapping["vip_api_ds_ips"] + str(i)].value)

  values["vip_api_ds_description"] = sheet[vipapids_detail_mapping["vip_api_ds_description"] + str(i)].value
  if values["vip_api_ds_description"] is None:
    values["vip_api_ds_description"] = ""
  else:
    values["vip_api_ds_description"] = values["vip_api_ds_description"].replace("'","''")
    
  values["vip_api_ds_type"] = sheet[vipapids_detail_mapping["vip_api_ds_type"] + str(i)].value    
  values["vip_api_ds_int_ext"] = sheet[vipapids_detail_mapping["vip_api_ds_int_ext"] + str(i)].value
  values["vip_api_ds_cert_int_ext"] = sheet[vipapids_detail_mapping["vip_api_ds_cert_int_ext"] + str(i)].value
  values["vip_api_ds_user_cn"] = sheet[vipapids_detail_mapping["vip_api_ds_user_cn"] + str(i)].value
  values["vip_api_ds_program"] = sheet[vipapids_detail_mapping["vip_api_ds_program"] + str(i)].value    
  values["vip_api_ds_mso"] = sheet[vipapids_detail_mapping["vip_api_ds_mso"] + str(i)].value
  values["vip_api_ds_stack"] = sheet[vipapids_detail_mapping["vip_api_ds_stack"] + str(i)].value  
  values["vip_api_ds_servicegroup"] = sheet[vipapids_detail_mapping["vip_api_ds_servicegroup"] + str(i)].value    
  values["vip_api_ds_servicename"] = sheet[vipapids_detail_mapping["vip_api_ds_servicename"] + str(i)].value
  values["vip_api_ds_datacenter"] = sheet[vipapids_detail_mapping["vip_api_ds_datacenter"] + str(i)].value
  values["vip_api_ds_env"] = sheet[vipapids_detail_mapping["vip_api_ds_env"] + str(i)].value    
  values["vip_api_ds_envside"] = sheet[vipapids_detail_mapping["vip_api_ds_envside"] + str(i)].value
  
  values["vip_api_ds_validfrom_dtm"] = sheet[vipapids_detail_mapping["vip_api_ds_validfrom_dtm"] + str(i)].value
  if type(values["vip_api_ds_validfrom_dtm"]) == "str":
    values["vip_api_ds_validfrom_dtm"] = datetime.datetime.strptime(values["vip_api_ds_validfrom_dtm"],"%Y-%m-%d %H:%M%S")
  elif values["vip_api_ds_validfrom_dtm"] is None:
    values["vip_api_ds_validfrom_dtm"] = "";

  values["vip_api_ds_validto_dtm"] = sheet[vipapids_detail_mapping["vip_api_ds_validto_dtm"] + str(i)].value
  if type(values["vip_api_ds_validto_dtm"]) == "str":
    values["vip_api_ds_validto_dtm"] = datetime.datetime.strptime(values["vip_api_ds_validto_dtm"],"%Y-%m-%d %H:%M%S")
  elif values["vip_api_ds_validto_dtm"] is None:
    values["vip_api_ds_validto_dtm"] = ""

  values["vip_api_ds_contactperson"] = sheet[vipapids_detail_mapping["vip_api_ds_contactperson"] + str(i)].value
  values["vip_api_ds_contactperson"]= values["vip_api_ds_contactperson"].replace("'","''")
  
  values["vip_api_ds_status"] = sheet[vipapids_detail_mapping["vip_api_ds_status"] + str(i)].value
  
  values["vip_api_ds_comment"] = sheet[vipapids_detail_mapping["vip_api_ds_comment"] + str(i)].value
  if values["vip_api_ds_comment"] is None:
    values["vip_api_ds_comment"] = ""
  else:
    values["vip_api_ds_comment"] = values["vip_api_ds_comment"].replace("'","''")

  
  values["vip_api_ds_sop_link"] = sheet[vipapids_detail_mapping["vip_api_ds_sop_link"] + str(i)].value
  values["vip_api_ds_port"] = sheet[vipapids_detail_mapping["vip_api_ds_port"] + str(i)].value    
  values["vip_api_ds_service_port"] = sheet[vipapids_detail_mapping["vip_api_ds_service_port"] + str(i)].value
  values["vip_api_ds_pool_members"] = sheet[vipapids_detail_mapping["vip_api_ds_pool_members"] + str(i)].value    
  values["vip_api_ds_patch_cycle"] = sheet[vipapids_detail_mapping["vip_api_ds_patch_cycle"] + str(i)].value
    
  # create values
  sqlqval = ""
  sqlval= "" 

  updateflag = fetchkeyval(cursor,values["vip_api_ds_hostname"],values["vip_api_ds_port"], values["vip_api_ds_type"])
  sqlstmt = ""
  if updateflag == 1:
    for mapkey in vipapids_detail_mapping:
          
      sqlval = sqlval + " " + mapkey + "='" + str(values[mapkey]) + "',"

    sqlstmt = "UPDATE " + conn["tablename"] + " SET " + sqlval[:-1] + " WHERE  vip_api_ds_hostname = '" + values["vip_api_ds_hostname"] +"' \
                and vip_api_ds_port = '" + str(values["vip_api_ds_port"]) + "' qand vip_api_ds_type='" + values["vip_api_ds_type"] + "'"
    print ("Updating ... ", values["vip_api_ds_hostname"], values["vip_api_ds_port"] )
  else:
    for mapkey in vipapids_detail_mapping:
      sqlqval = sqlqval + mapkey + ","
      sqlval = sqlval + "'" + str(values[mapkey]) + "',"
          
    sqlstmt = "INSERT INTO "+ conn["tablename"]+ "(" + sqlqval[:-1]+ ") VALUES (" + sqlval[:-1] +")"
    print ("Inserting ... ", values["vip_api_ds_hostname"], values["vip_api_ds_port"])
      
  insertupdatestmt[i] = sqlstmt
    
print ("Starting insertion....")
# now insert
for k in insertupdatestmt:
    print ("Inserting Record: ", k)
    insertupdatedata(cursor, insertupdatestmt[k])

print ("Program finished....")  
wb.close
                    
                
                
                
            
