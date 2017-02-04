'''
Created on 4 Aug 2015

@author: marek
'''

import psutil

# Storing previous counter values for difference calculation
prev_ctr_val=dict()

def delta(dom_name, param_name, new_val):
    if dom_name not in prev_ctr_val:
        prev_ctr_val[dom_name]=dict()
    if param_name not in prev_ctr_val[dom_name]:
        prev_ctr_val[dom_name][param_name] = new_val
     
    rslt = new_val - prev_ctr_val[dom_name][param_name]
    prev_ctr_val[dom_name][param_name] = new_val
    return rslt

def get_process_performance_data(pid, dom_name):
    
    proc = psutil.Process(pid)
    params = dict()

    cpu_times = proc.cpu_times()
    memory_percent = proc.memory_percent()
    io_counters = proc.io_counters()
    mem_info = proc.memory_info_ex()
    
    params['cpu_usr'] = delta(dom_name, 'cpu_usr', cpu_times[0])
    params['cpu_sys'] = delta(dom_name, 'cpu_sys', cpu_times[1]) 
    params['memory_percent'] = memory_percent
    params['mem_rss'] = mem_info[0]
    params['mem_vms'] = mem_info[1]
    params['mem_shr'] = mem_info[2]
    params['mem_txt'] = mem_info[3]
    params['mem_lib'] = mem_info[4]
    params['mem_data'] = mem_info[5]
    params['mem_drt'] = mem_info[6]
    params['io_read_bytes'] = delta(dom_name, 'io_read_bytes', io_counters[2])
    params['io_write_bytes'] = delta(dom_name, 'io_write_bytes', io_counters[3])
     
    kvm_metrics = KvmMetrics(**params)

    return kvm_metrics

class KvmMetrics():
    def __init__(self,cpu_usr=0,cpu_sys=0,memory_percent=0, mem_rss=0, mem_vms=0,
                 mem_shr=0, mem_txt=0, mem_lib=0, mem_data=0, mem_drt=0, 
                 io_read_bytes=0,io_write_bytes=0, **kwargs):    
        self.cpu_usr = cpu_usr
        self.cpu_sys = cpu_sys
        self.memory_percent = memory_percent
        self.mem_rss = mem_rss
        self.mem_vms = mem_vms
        self.mem_shr = mem_shr
        self.mem_txt = mem_txt
        self.mem_lib = mem_lib
        self.mem_data = mem_data
        self.mem_drt = mem_drt
        self.io_read_bytes = io_read_bytes
        self.io_write_bytes = io_write_bytes
        
    def as_list(self):
        row = [self.cpu_usr, self.cpu_sys, self.memory_percent, self.mem_rss, self.mem_vms,
               self.mem_shr, self.mem_txt, self.mem_lib, self.mem_data, self.mem_drt,
               self.io_read_bytes, self.io_write_bytes]
        return row
