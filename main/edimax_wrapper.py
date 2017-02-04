'''
Created on 4 Aug 2015

@author: marek
'''
import requests
from bs4 import BeautifulSoup
import logging
import nmap

EDIPLUG_PASSW = "1234"

logger = logging.getLogger("edimax")

MY_WLAN_INET_ADDR = '192.168.1.101'

def find_edimax_devices():
    """
    Returns the available Edimax smartplugs available in the current network
    """
    nm = nmap.PortScanner()
    nm.scan(hosts = MY_WLAN_INET_ADDR + '/24', arguments='-sn')
    
    devices = []
    for host in nm.all_hosts():
        try:
            # Make sure PASSWORD for Edimax is correct, otherwise it will be treated as not found!
            power = edimax_get_power(host)
            devices.append(host)
            logger.debug("Edimax found on host: {0} ".format(host))
            print("Edimax found on host: {0} ".format(host))
        except:
            logger.debug("No edimax present on {0} ".format(host))

    return devices

# Get power sample according to the Edimax protocol.
# For more info, see http://sun-watch.net/index.php/eigenverbrauch/ipschalter/edimax-protokoll/
def edimax_get_power(ip_addr="192.168.1.101"):

    request = """<?xml version="1.0" encoding="UTF8"?><SMARTPLUG id="edimax"><CMD id="get">
    <NOW_POWER><Device.System.Power.NowCurrent>
    </Device.System.Power.NowCurrent><Device.System.Power.NowPower>
    </Device.System.Power.NowPower></NOW_POWER></CMD></SMARTPLUG>"""

    response = requests.post("http://{0}:10000/smartplug.cgi".format(ip_addr), auth=("admin", EDIPLUG_PASSW), data=request)
    soup = BeautifulSoup(response.text, features="xml")
    power = soup.find(name="Device.System.Power.NowPower").get_text()
    
    return float(power)

if __name__ == "__main__":
    print find_edimax_devices()
