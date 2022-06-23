#!/bin/sh

### This script will pull the certs valid from, valid to, subject to get common name and issuer details
ifilename="qa_sit_cdp_urls.txt" # change the file name
ofilename="output_$ifilename"
rm -f $ofilename
echo "program started"
while read -r line
do
    #echo $line
    res=`echo | openssl s_client -showcerts -connect "$line" 2>/dev/null | openssl x509 -inform pem -noout -startdate -enddate -subject -issuer`

    #save to the output file
    echo $line $res >> $ofilename

done < "$ifilename"

echo "program ended"

exit