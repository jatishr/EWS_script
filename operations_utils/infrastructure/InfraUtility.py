#############################################################
# Name: InfraUtility.py                                     #
# Start Date: 8/24/2021                                     #
# Version: 1.0                                              #
# Description: This script will run utility                 #
# Author: Sushant Kumar                                     #
#############################################################

import re
from datetime import datetime
from dateutil import tz
import time
import os
import subprocess
import openpyxl
import sys
import shutil

# check what is the request number 1 = Create URLs , 2 = Parse output to sheet
if len(sys.argv) < 2:
    print ("Please provide the option 1 OR 2.")
    sys.exit(0)

opt = int(sys.argv[1])
if opt > 2 or opt <= 0:
    print ("Please provide the option 1 OR 2.")
    sys.exit(0)

# run through End points excel sheet
# open and assign columns
tab = "VIPAPIDataSource"

# open excel sheet; data_only = True to avoid any formula value
filename = 'vipapids.xlsx'
wb = openpyxl.load_workbook(filename)
sheet = wb[tab]
row_count = sheet.max_row

if opt == 1:
    location = "urls/input/"
    # need to create files for all environment
    fhandle_prod_dr = open(location + "prod_dr_urls.txt","w")
    fhandle_uat_qa_ncw = open(location + "uat_qa_ncw_urls.txt","w")
    fhandle_uat_cdp = open(location + "uat_cdp_urls.txt","w")
    fhandle_qa_sit_cdp = open(location + "qa_sit_cdp_urls.txt","w")

    # Now read each row and then update file accordingly
    i = 2
    for i in range(2, row_count):

        if not sheet["A" + str(i)].value:
            break

        hostname = sheet["A" + str(i)].value
        ports = str(sheet["C" + str(i)].value)
        host_type = sheet["E" + str(i)].value
        data_center = sheet ["P" + str(i)].value
        environment = sheet ["Q" + str(i)].value
        active = sheet["W" + str(i)].value

        # now based on the data_center and environment write into different files
        # only VIPs or APIs we will create the file
        if (host_type == "VIP" or host_type == "API") and (active == "Active"):
            # there will be multiple port that URL may support. It will be separated by comma
            splitport = ports.split(",")
            for port in splitport:
                port = port.strip()
                hostname = hostname.strip()
                if re.search("NC(E|W)?",data_center) and re.search("PROD|DR",environment,re.IGNORECASE):
                  fhandle_prod_dr.write(hostname +":"+port+"\n")

                if re.search("NCW",data_center) and re.search("UAT|QA",environment,re.IGNORECASE):
                  fhandle_uat_qa_ncw.write(hostname +":"+port+"\n")

                if re.search("CDP",data_center) and re.search("UAT",environment,re.IGNORECASE):
                  fhandle_uat_cdp.write(hostname +":"+port+"\n")

                if re.search("CDP",data_center) and re.search("SIT|QA|Test",environment,re.IGNORECASE):
                  fhandle_qa_sit_cdp.write(hostname +":"+port+"\n")

    fhandle_prod_dr.close()
    fhandle_uat_qa_ncw.close()
    fhandle_uat_cdp.close()
    fhandle_qa_sit_cdp.close()
    wb.close()   
    
elif opt == 2:
    
    # it will open the output file and update to the sheet
    # after update move the file to backup with timestamp
    outputlocation = "urls/output/"
    backuplocation = "urls/output/backup/"
    
    # create a dictinoary to hold sheet pointer
    i = 2
    hostpointer = {}
    for i in range(2, row_count):
        if not sheet["A" + str(i)].value:
            break

        hostname = sheet["A" + str(i)].value
        hostname = hostname.strip()
        ports = str(sheet["C" + str(i)].value)

        splitport = ports.split(",")
        for port in splitport:
            port = port.strip()

            hostpointer[hostname + ":" + port] = i
            

    # Initialize timezone
    from_zone = tz.tzutc()
    to_zone = tz.tzlocal()
    
    # we have row number; now run through each output file and then update the columns
    for root,dirs,files in os.walk (outputlocation):

        for f in files:

            if re.search("backup",root):
                break
            
            fhnd = open(root+f,"r")
            comment = ""
            for line in fhnd:
                # split on space but the first element will what we looking for
                splitline = line.split(" ")
                if splitline[0] in hostpointer:
                    print ("Extracting Information...",splitline[0])

                    # split to get hostname and port
                    host_port = splitline[0].split(":")
                    
                    extract = re.findall(r'notBefore=([\w\d:\s]+)notAfter=([\w\d:\s]+)subject=.*CN\s?=([\w\d\-\.\s]+)issuer=.*CN\s?=([\w\s\d]+)\n',line)
                    # the order Valid From, Valid To, Common Name, Issuer (If not Charter Communication then External)
                    # the times will be GMT have to convert into CST
                    validfrom = extract[0][0].strip()
                    validfromutc = datetime.strptime(validfrom, '%b %d %H:%M:%S %Y GMT')
                    validfromutc = validfromutc.replace(tzinfo=from_zone)
                    validfromutc = validfromutc.astimezone(to_zone)
                    
                    validto = extract[0][1].strip()
                    validtoutc = datetime.strptime(validto, '%b %d %H:%M:%S %Y GMT')
                    validtoutc = validtoutc.replace(tzinfo=from_zone)
                    validtoutc = validtoutc.astimezone(to_zone)

                    commonname = extract[0][2].strip()
                    issuer = extract[0][3].strip()
                    cert_ext_int = ""

                    if re.search('Charter Communications',issuer):
                        cert_ext_int = "Internal"
                    else:
                        cert_ext_int = "External"

                    # now we have all variables update the sheet
                    #Common Name= F; Certs/Username Valid From = S; Certs/Username Valid To = T; Comment = V
                    sheet["F" + str(hostpointer[splitline[0]])].value = commonname
                    sheet["S" + str(hostpointer[splitline[0]])].value = validfromutc
                    sheet["T" + str(hostpointer[splitline[0]])].value = validtoutc
                    sheet["I" + str(hostpointer[splitline[0]])].value = cert_ext_int

                    if len(comment) == 0:
                        comment = sheet["V" + str(hostpointer[splitline[0]])].value

                    if comment:
                        comment = comment + "; " + host_port[1] + ": Issuer = "  + issuer
                    else:
                        comment = host_port[1] + ":Issuer = "  + issuer
 
            fhnd.close()
            
            # move file to backup using timestamp
            tm = datetime.strftime(datetime.now(),'%Y%m%d%H%M%S')
            shutil.move(root+f,root+"//backup//"+f+"_" +tm)

        wb.save(filename)
