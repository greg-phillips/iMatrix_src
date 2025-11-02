# Correct setup of udhcp with multiple instances on a Quake QConnect running busybox

## Backgroud
Read docs/Fleet-Connect-Overview.md
Read docs/NETWORKING_SYSTEM_COMPLETE_GUIDE.md
Read Fleet-Connect-1/init/imx_client_init.c
Read all iMatrix/IMX_Platform/LINUX_Platform/networking source files
The following three files provide some internet search guides on the setup up of udhcpd in a standard busybox system. 
Use them as reference.
Cross validate if needed.
Read docs/udhcpd/udhcpd_perplexity.md
Read docs/udhcpd/udhcpd_gpt5.md
Read docs/udhcpd/udhcpd_gemini.md
Read all scripts and files in docs/udhcpd/examples

The Quake Connect gateway runs busybox linux.
Separate udhcpd configurations are needed for correct operation.
the Quake QConnect Busybox implemenation uses the runit facility to run alternative default scripts. 
If the uduchpd directory is present in the to /usr/qk/etc/sv/ directory this will be used instead of the default.
The udbcpd direcory in the docs/udhcpd
/examples is the default script.



## Requirement
Create a version of the scripts to run one or both udhcpd servers with independant udhcpd.conf files that are stored in the /etc/nertwork directory. for example udhcpd.eth0.conf and udhcpd.wlan0.conf

After reviewing all the information presented about setting up the independant udhcpd configuration write a plan to add this functionlity to the existing network initialzation.
The plan must include writing all needed configuraton scripts and files to the /usr/qk/etc/sv/ on a network reconfiguration event.

Ask any follow up questions needed to clarify the implementation. This is a major feature so create a branch to test it before we merge it back to the main Aptera_1 branches for both iMatrix and Fleet-Connect-1 repositories.
