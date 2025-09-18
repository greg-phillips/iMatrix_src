#
# Script to upload a list of sensors to the iMatrix API range 511 to 537
#

for i in {511..537}; do
    python3 upload_internal_sensor.py  -u superadmin@imatrixsys.com -p passw0rd123 -f sensor_${i}.json
done