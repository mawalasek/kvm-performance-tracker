'''
Created on 20 Aug 2015

@author: marek
'''
import shlex
import subprocess
import signal as sig

# PERF-KVM commands (make sure the right 'kallsyms' and 'modules' files are in the right directory!):
KVM_RECORD = 'perf kvm --guest --guestkallsyms=../perf_res/guest-kallsyms --guestmodules=../perf_res/guest-modules record -a -o ../perf_output/perf.data.guest'
KVM_REPORT = 'perf kvm --guest --guestkallsyms=../perf_res/guest-kallsyms report -i ../perf_output/perf.data.guest.old --sort=comm'

'''Example output:

# Samples: 30  of event 'cycles'
# Event count (approx.): 4397116
#
# Overhead  Command
# ........  .......
#
    51.43%    :5702
    36.57%    :5444
    12.00%    :5732

'''

class PerfKVMWrapper():
    
    record = None
    record_comm = None
    report_comm = None
     
    def __init__(self):
        self.record_comm = shlex.split(KVM_RECORD)
        self.report_comm = shlex.split(KVM_REPORT)
    
    def collect_perf_kvm_data(self):
        
        sample = {}
        
        if self.record != None: # For first iteration, skip reporting, jump to init record process
            # Stop perf record
            self.record.send_signal(sig.SIGINT)
          
            # Report data
            rep = subprocess.Popen(self.report_comm, stdout=subprocess.PIPE)
            rep_out = rep.stdout.read()
            rep.kill()

            sample = self.report_as_dict(rep_out)
          
        # Start new perf record process
        self.record = subprocess.Popen(self.record_comm, stdout=subprocess.PIPE)
        
        return sample
        
    '''Parses the perf report output to a dictionary (dom-pid mapping to counter value)'''
    def report_as_dict(self, rep_out):
        
        sample_dict = {}
        
        for ln in rep_out.split('\n'):
            
            if not ln.startswith('#') and ln != '':
                
                tpl = ln.split(':')
                tpl[1] = int((tpl[1].strip()))
                tpl[0] = float(tpl[0].strip().replace('%', '')) / 100
                
                #map value (ctr percent) to key (dom pid)
                sample_dict[tpl[1]] = tpl[0]
            else: 
                if "Event count (approx.)" in ln:
                    sample_dict['kvm-total-cyc'] = int(ln.split(':')[1].strip())
        
        return sample_dict
    