#
# Script to link a number of sensors to a product from 508 to 537
#

for i in {508..537}; do
    python3 link_sensor.py -u superadmin@imatrixsys.com -p passw0rd123 -pid 1235419592 -sid ${i}
done

