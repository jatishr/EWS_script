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
mconfig.read("EWSVIPAPIDS.ini")

# create global variables
# initialize dictionary

conn = mconfig["vipapidsdb"]
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
    
def fetchkeyval (cursor, identifierid):

  flag = 0
  try:
    sqlstmt = "SELECT TOP 1 * FROM " + conn["cert_pass_tablename"] + " WHERE identifier_id = '" + str(identifierid) + "'"
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

try:
    # the date is fixed since this feature is rolled in 2021
    query = "select vip_api_ds_id, vip_api_ds_hostname, vip_api_ds_program, vip_api_ds_type, vip_api_ds_validto_dtm, vip_api_ds_sop_link, \
         datediff(Day,getdate(),vip_api_ds_validto_dtm) as expiry_date \
         from "+ conn["tablename"] +" where datediff(Day,getdate(),vip_api_ds_validto_dtm) <=45 \
         and vip_api_ds_status = 'Active' and vip_api_ds_validto_dtm >= '2019-01-01'"
    cursor.execute(query)
    results = cursor.fetchall()
    if results:

        for row in results:
            # insert into ews_certs_password_expr if no data found else leave it
            updateflag = fetchkeyval(cursor, row[0])
            dt = row[4]
            if dt == None:
                dt = ""
            else:
                dt = datetime.datetime.strftime(row[4], "%Y-%m-%d %H:%M:%S")

            if updateflag == 0:

                ident_type = row[3]
                if row[3] == 'VIP' or row[3] == "API":
                  ident_type = "CERTS"
                elif re.search("DataSource|DS",row[3],re.IGNORECASE):
                  ident_type = "Password"

                if row[5] == None:
                    row[5] = ""
                
                insertstmt = "INSERT INTO "+conn["cert_pass_tablename"]+" (identifier_id, identifier, program, ident_type, exp_date_time, sop_link) \
                      values ('" + str(row[0]) + "', '" + row[1]+ "', '" + row[2]+ "', '" + ident_type + "', '" + dt + "','" + row[5]+ "')"
                print ("Inserting Identifier...", row[0])
                insertupdatedata(cursor, insertstmt)
            else:
                updatestmt = "update " + conn["cert_pass_tablename"]+ " set exp_date_time = '" + dt + "' where identifier_id ='" + str(row[0]) +"'" 
                print ("Updating Identifier...", row[0])
                insertupdatedata(cursor, updatestmt)
        
        
    # Now run through ews_certs_password_expr table to see if entry is in there to:
    # 1. If the cert/password ticket or actions_taken is not blank then insert into vip_api_datasource_hist if no row found else update the row
    # 2. If the cert/password expiry date is < today and ticket or actions_taken is updated then delete the row

    certs_pass_query = "select identifier_id, identifier, ticket_num, actions_taken, exp_date_time from " + conn["cert_pass_tablename"]
    cursor.execute(certs_pass_query)
    cert_pass_res = cursor.fetchall()

    if cert_pass_res:

        for certsrow in cert_pass_res:

            # check ticket number or actions taken
            ticket_num = certsrow[2]
            if ticket_num == None:
                ticket_num = ""
                
            actions_taken = certsrow[3]
            if actions_taken == None:
                actions_taken = ""

            identifier_id = certsrow[0]

            if len(ticket_num) > 0 or len(actions_taken) > 0:
                # Bug 10/26/2021 - OR query is bringing duplicate entry. 
                hist_query = "select vip_api_ds_hist_id, identifier_id, vip_api_ds_actionstaken, vip_api_ds_ticket_num, vip_api_ds_updated_dtm from " + conn["hist_tablename"] + " where vip_api_ds_ticket_num ='" + ticket_num + "' \
                         and identifier_id = '"+ str(identifier_id) +"' order by vip_api_ds_updated_dtm desc"
                
                cursor.execute(hist_query)
                hist_res = cursor.fetchall()
                dt = datetime.datetime.strftime(datetime.datetime.today(),"%Y-%m-%d %H:%M:%S")
                if not hist_res:
                    hist_insert_update = "insert into " + conn["hist_tablename"] + " (identifier_id, vip_api_ds_actionstaken, vip_api_ds_ticket_num, \
                            vip_api_ds_updated_dtm) values ('" + str(certsrow[0]) + "', '" + actions_taken + "', '" + ticket_num +  "','"+ dt +"')"
                else:
                    hist_insert_update = "update " + conn["hist_tablename"] + " set vip_api_ds_actionstaken ='" + actions_taken + "', vip_api_ds_ticket_num='" + ticket_num +  "' where vip_api_ds_hist_id = '" + str(hist_res[0][0]) +"'"
              
                insertupdatedata(cursor, hist_insert_update)

            # check the exp_datetime if its < todays date then delete the row
            expdate = certsrow[4]
            if expdate:
                if expdate < datetime.datetime.today():
                    cert_delete = "delete from " + conn["cert_pass_tablename"] + " where identifier_id = '" + str(certsrow[0]) + "'"
                    insertupdatedata(cursor, cert_delete)

            # 10/11/2021 - Sushant Kumar. Check if date has been updated vip_api_datasource. If expiry date from the vip_api_datasource is greater than
            # date in ews_certs_password_expr then delete the row with understanding that date has been updated
            certs_check_query = "SELECT DATEDIFF(DAY, b.vip_api_ds_validto_dtm, a.exp_date_time) FROM  " + conn["cert_pass_tablename"] + " a \
                                inner join " + conn["tablename"] + " b on b.vip_api_ds_id = a.identifier_id where b.vip_api_ds_id = '" + str(certsrow[0]) +"'"
            cursor.execute(certs_check_query)
            cert_check_res = cursor.fetchall()
            if cert_check_res:
                # if days remaining is < 0 then delete the row
                if cert_check_res[0][0] < 0:
                    cert_delete = "delete from " + conn["cert_pass_tablename"] + " where identifier_id = '" + str(certsrow[0]) + "'"
                    print (" deleting identifier.. ",certsrow[0])
                    insertupdatedata(cursor, cert_delete)

        # Now since all activities are done drop a mail
        # check what is current in the data in the cert table. Also get the overall certs information
        # if no record then dont send blank mail
        certs_query = "select identifier_id, identifier, program, ident_type, exp_date_time, datediff(Day,getdate(),exp_date_time) as exp_days, ticket_num, actions_taken from " + conn["cert_pass_tablename"]
        cursor.execute(certs_query)
        results = cursor.fetchall()

        tempbody = ""

        if results:
            mailbody = """\
<html>
 <body>
  <table>
   <tr>
    <th>Identifier Id</th>
    <th>Identifier</th>
    <th>Program</th>
    <th>Ident_type</th>
    <th>Expiration Date</th>
    <th>Days to Expire</th>
    <th>Ticket<th>
   </tr>
"""

            for rows in results:
                identifier_id = str(rows[0])
                exp_date_time = rows[4]
                if exp_date_time == None:
                    exp_date_time = ""
                else:
                    exp_date_time = datetime.datetime.strftime(rows[4], "%Y-%m-%d %H:%M:%S")

                exp_days = rows[5]

                if exp_days == None:
                    exp_days = ""
                else:
                    exp_days = str(rows[5])

                ticket_num = rows[6]
                if ticket_num == None:
                    ticket_num  = ""
                else:
                    ticket_num = str(rows[6])

                actions_taken = rows[7]
                if actions_taken == None:
                    actions_taken  = ""
                else:
                    actions_taken = str(rows[7])

                tempbody = tempbody + "<tr><th>" + identifier_id + "</th><th>" + rows[1] + "</th><th>" + rows[2] + "</th><th>" + rows[3] + "</th><th>" + exp_date_time + "</th><th>" + exp_days + " \
                    </th><th>" + ticket_num + "</th><th>" + actions_taken + "</th></tr>"
            
            mailbody = mailbody + tempbody + """\
  </table>
 </body>
</html>
"""
            mailconf = mconfig["mail"]
            send_email(mailbody, mailconf["subject"], "", mailconf["recipient"])
            print ("Mail sent.. Exiting the application...")

except Exception as e:
  print ("An error occured...Please check...",e)

  
