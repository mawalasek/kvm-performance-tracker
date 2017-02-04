'''
Created on 4 Aug 2015

@author: marek
'''
import os
import libvirt
import psutil
import time
from blinker import signal
from datetime import datetime
from xml.dom.minidom import parse
from edimax_wrapper import edimax_get_power
import threading 
import sys
from csv_logger import CSVLogger
import psutil_wrapper
from perf_kvm_wrapper import PerfKVMWrapper
from perf_stat_wrapper import PerfStatWrapper
from xml.etree import ElementTree as ET
 
if __name__ == '__main__':
    pass

# Smartplug's IP address - find out using edimax_wrapper.py
EDIMAX_IP = '192.168.1.103'

# Where to put the logs
LOG_DIR_LOCAL = "../logs"
 
# Where the configuration .xml files for the existing domains are located
DOMAIN_CONFIG_DIR = '/var/run/libvirt/qemu/'

# Sampling rate (seconds)
SAMPLING_RATE = 1
 
# Mapping of the names to the pids (pid=<mapping>[name]) of the currently running KVM domains
domain_pids={}

# Mapping of the pids to the names (name=<mapping>[pid]) of the currently running KVM domains
domain_names={}

# Mapping of the names to the list of network interface names (iface_name=<mapping>[kvm_name]) used by the currently running domains
domain_net_ifaces={}

# Mapping of the names to the domain objects
domain_obj_refs={}

# Signal for triggering the collection of one sample
get_sample_signal = signal("get_sample") 

# Signal for passing the sample data for further processing
data_sampled_signal = signal('data_sampled_signal')


'''Detects all running KVM processes and updates the name-to-pid assignment'''        
def update_running_domains():
    
    # First, determine domains using libvirt
    libvirt_connection = libvirt.open("qemu:///system")
    print libvirt_connection.listDomainsID()
    running_domains = [libvirt_connection.lookupByID(domId) for domId in libvirt_connection.listDomainsID()]
    
    # Then, using domain names, extract the PIDs of the running domains from the configuration files
    for dom in running_domains:
        xml_data = parse(DOMAIN_CONFIG_DIR + dom.name() + '.xml')
        pids = [elt.getAttribute("pid") for elt in xml_data.getElementsByTagName('domstatus')  ]
        pid = pids.pop()
        
        # Also, get all virtual network interfaces associated with the domain.
        # This is necessary for network performance data collection.
        xe = ET.fromstring(dom.XMLDesc(0))
        net_ifaces = []
        for iface in xe.findall('.//devices/interface'):
            iface_name = iface.find('target').get('dev')
            net_ifaces.append(iface_name)
        
        # Update the global dictionaries:
        domain_pids[dom.name()] = int(pid)
        domain_names[pid] = dom.name()
        domain_net_ifaces[dom.name()] = net_ifaces
        domain_obj_refs[dom.name()] = dom

# Thread class responsible for sampling the performance data
class DataSampler(threading.Thread):

    # Dictionary for storing previous counter values for difference (delta) calculation
    prev_ctr_val=dict()

    def __init__(self, edimax_ip):
        super(DataSampler, self).__init__()
        self.perf_stat_wrapper = PerfStatWrapper()
        self.perf_kvm_wrapper = PerfKVMWrapper()
        self.edimax_ip = edimax_ip
        self.running = False
        get_sample_signal.connect(self.on_get_sample)

    def run(self):
        self.running = True
        p = psutil.Process(os.getpid())
        p.cpu_affinity([0]) #the process is forced to run on the first CPU core

    def close(self):
        pass

    # Calculates the difference (delta) between the currently sampled and the previous counter value
    def delta(self, dom_name, param_name, new_val):
        if dom_name not in self.prev_ctr_val:
            self.prev_ctr_val[dom_name]=dict()
        if param_name not in self.prev_ctr_val[dom_name]:
            self.prev_ctr_val[dom_name][param_name] = new_val

        rslt = new_val - self.prev_ctr_val[dom_name][param_name]
        self.prev_ctr_val[dom_name][param_name] = new_val
        return rslt

    # Returns the per-domain performance data sample.
    def collect_kvm_performance_data(self, power):

        # First, get the CPU cycles collected with PERF-KVM:
        perf_kvm_output = self.perf_kvm_wrapper.collect_perf_kvm_data()

        for domain_name in domain_pids.keys():
            try:
                pid = domain_pids[domain_name]

                # PSUTIL
                sample = self.collect_psutil_data(pid, domain_name)

                # PERF-KVM
                self.collect_perf_kvm_data(sample, perf_kvm_output, pid, power)

                # LIBVIRT
                self.collect_libvirt_data(sample, domain_name)

                # PERF-STAT
                self.collect_perf_stat_data(sample, pid)

                data_sampled_signal.send({"dom_name":domain_name, "performance_data": sample})

            except psutil.NoSuchProcess:
                domain_pids.pop(domain_name)

    def collect_psutil_data(self, pid, domain_name):
        return psutil_wrapper.get_process_performance_data(pid, domain_name).as_list()

    def collect_perf_kvm_data(self, sample, perf_kvm_output, pid, power):
        cyc_per_dom = 0
        cyc_total = 0
        if 'kvm-total-cyc' in perf_kvm_output:
            cyc_total = perf_kvm_output['kvm-total-cyc']
        if pid in perf_kvm_output:
            cyc_per_dom = perf_kvm_output[pid]
        sample.insert(0, cyc_total)
        sample.insert(0, cyc_per_dom)
        sample.insert(0, power)
        sample.insert(0, datetime.now().strftime("%d/%m/%Y %H:%M:%S"))

    def collect_libvirt_data(self, sample, domain_name):
        dom = domain_obj_refs[domain_name]
        rx_total = 0
        tx_total = 0
        for iface_name in domain_net_ifaces[domain_name]:
            rx, _, _, _, tx, _, _, _ = dom.interfaceStats(iface_name)
            rx_total += rx
            tx_total += tx
        sample.append(self.delta(domain_name, 'bytes_sent', tx_total))
        sample.append(self.delta(domain_name, 'bytes_received', rx_total))

    def collect_perf_stat_data(self, sample, pid):
        perf_stat_output = self.perf_stat_wrapper.collect_perf_stat_data(pid)
        if 'instructions' in perf_stat_output:
            instr = perf_stat_output['instructions']
        else:
            instr = 0
        if 'cpu-clock' in perf_stat_output:
            cpu_clock = perf_stat_output['cpu-clock']
        else:
            cpu_clock = 0
        if 'branch-misses' in perf_stat_output:
            br_miss = perf_stat_output['branch-misses']
        else:
            br_miss = 0
        if 'cache-misses' in perf_stat_output:
            cache_miss = perf_stat_output['cache-misses']
        else:
            cache_miss = 0
        if 'task-clock' in perf_stat_output:
            task_clock = perf_stat_output['task-clock']
        else:
            task_clock = 0
        if 'cpu-cycles' in perf_stat_output:
            cycles = perf_stat_output['cpu-cycles']
        else:
            cycles = 0

        sample.append(instr)
        sample.append(cpu_clock)
        sample.append(br_miss)
        sample.append(cache_miss)
        sample.append(task_clock)
        sample.append(cycles)

    def on_get_sample(self, msg):

        # Get current domain information
        update_running_domains()

        # Get physical power measurement from EdiPlug
        power = edimax_get_power(EDIMAX_IP)

        # Get performance data of all running KVMs
        self.collect_kvm_performance_data(power)

def main(args):
    
    #init local CSV file logger
    csv_writer = CSVLogger(LOG_DIR_LOCAL, is_local=True)
        
    #init data sampling thread
    sampler = DataSampler(EDIMAX_IP)
    sampler.setDaemon(True)

    get_sample_signal = signal("get_sample")
    
    try:
        if sampler.running == False:
            sampler.start()  
        while True:
            #tell data sampler to collect sample
            get_sample_signal.send({})
            #wait with the next signal
            time.sleep(SAMPLING_RATE)
    
    #Kill the app and the child thread when user hits Ctrl+C
    except(KeyboardInterrupt, SystemExit):
        sampler.running = False
        sampler.join()
        sampler.close()
        sys.exit()

if __name__ == '__main__':
    main(sys.argv)

        
