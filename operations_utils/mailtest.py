import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

def send_email(mail_body="", subject=""):
    fromaddr = "abc@charter.com"
    toaddr_list = [
     "sushant.kumar@charter.com"
    ]
    passwd = "need to create gmail app to get password"
    msg = MIMEMultipart()

    msg['From'] = fromaddr
    msg['To'] = ", ".join(toaddr_list)
    if(subject):
        msg['Subject'] = subject
    else:
        msg['Subject'] = "subject of mail."

    body = mail_body

    msg.attach(MIMEText(body, 'plain'))

    # send message with attachment
    filename = "mail.txt"

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
    s.sendmail(fromaddr, toaddr_list, text)
    s.quit()

send_email("abc-dec","hi")
