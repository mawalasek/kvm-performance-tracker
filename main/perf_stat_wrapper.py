'''
Created on 20 Aug 2015

@author: marek
'''
import shlex
import subprocess
import signal as sig

PERF_STAT_CMD = 'perf stat -x, -e cpu-clock:G,instructions:G,cache-misses:G,branch-misses:G,task-clock:G,cpu-cycles:G -p '

''' Example command-line output:
        4.269998,cpu-clock:G
        335762,instructions:G
        38527,cache-misses:G
        8139,branch-misses:G
        4.269935,task-clock:G
        1429826,cpu-cycles:G
'''

class PerfStatWrapper():
    
    # Dict containing the mapping of a pid to a stat command (for every guest PID a perf stat command is started):
    stat = {}
    
    def __init__(self):
        pass
    
    def collect_perf_stat_data(self, pid):
        
        counters = {}
        
        if pid in self.stat and self.stat[pid] is not None: #For first iteration, skip reporting, jump to init record process
            
            # Stop perf stats
            self.stat[pid].send_signal(sig.SIGINT)

            (stat_out, stat_err) = self.stat[pid].communicate()

            counters = self.stat_as_dict(stat_err)
          
        # Start new perf stats
        stat_comm = shlex.split(PERF_STAT_CMD)
        stat_comm.append(' ' + str(pid)) # Append the PID as the last command arg
        
        # Store the running process for reference in the next iteration:
        self.stat[pid] = subprocess.Popen(stat_comm, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        return counters
        
    # Parses the perf stat output to a dictionary (mapping counter name to counter value)'''
    def stat_as_dict(self, stat_out):
        
        counters = {}
        
        for ln in stat_out.split('\n'):
            if not ln.startswith('Performance') and ln != '':
                
                tpl = ln.split(',')

                # Caution: values might be missing. Here, we replace them with 0 for simplicity:
                try:
                    tpl[0] = float(tpl[0].strip())
                except ValueError:
                    tpl[0] = float(0)
                
                # Counter name as key:
                ctr_name = tpl[1].split(':')[0].strip()    
                counters[ctr_name] = tpl[0]
        
        return counters
    
    