'''
Created on 4 Aug 2015

@author: marek
'''
import csv
from blinker import signal
import os
from datetime import datetime

class CSVLogger(object):
    def __init__(self, log_file_dir, is_local=False, filename="{dom_name}.log_{date}.csv"):
        
        self.is_local = is_local
        
        self.log_file_dir = log_file_dir
        
        if self.is_local:
            self.sample_signal = signal("data_sampled_signal")
        else:
            self.sample_signal = signal("sample_received_signal")
        
        self.filename_template = filename
         
        #Listen to sample_signal signal with the on_sample method:
        self.sample_signal.connect(self.on_sample)
 
    def close(self):
        self.sample_signal.disconnect(self.on_sample)
 
    def on_sample(self, msg):
        self.write_row(msg["dom_name"], msg["performance_data"])
 
    def write_row(self, dom_name, data):
        file_name = self.filename_template.format(dom_name=str(dom_name), date=datetime.today().strftime('%Y-%m-%d'))
        
        # TODO Avoid opening and closing a file on each state message for efficiency
        log_file = open(os.path.join(self.log_file_dir,file_name), "ab")
        
        # Use comma as a delimiter (for Excel)
        csv_writer = csv.writer(log_file, delimiter=',', quotechar='"')
        csv_writer.writerow(data)
        
        log_file.close()
        
        