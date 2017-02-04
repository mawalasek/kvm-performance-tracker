# KVM performance tracker
This project demonstrates how a collection of different Linux tools can be used to monitor resource consumption in a kernel-based virtual machine (KVM) environment.
For every running VM the individual performance metrics, such as CPU cycles, allocated memory, or disk & network operations are collected. Additionally, the instantaneous power consumption of the whole platform (physical machine) is collected using an Edimax smartplug. The latter metric is particularly useful for evaluating the accuracy of the presented tool, e.g. via regression models.
The results are stored locally under the /logs directory. For every running VM a CSV file is created.

# Run the Tracker App
Issue `python tracker_app.py` to start tracking KVM performance. Install the additional modules, if necessary (see python console output for missing modules).

# Used tools
## perf-kvm
Perf-kvm is used to sample *CPU cycles* consumed by each running VM. The tool was originally developed to be used via the command line in a “record-report” manner. This means that within every iteration the Tracker App must issue three commands to perf-kvm: the first command stops the perf-kvm recording process started in the previous iteration, and the second one reads (“reports”) the output file. Finally, after the output has been parsed by the Tracker App, and the output file can be overriden, the third command launches the next recording process. For more info on perf-kvm, please refer, e.g., to the [Ubuntu manual](http://manpages.ubuntu.com/manpages/trusty/man1/perf-kvm.1.html "Ubuntu manpages - perf kvm").

## psutil
Psutil is a Python library which allows the access to system-wide and process-specific performance counters. In the proposed design, psutil is used to gather the amount of *main memory* (in bytes) allocated to each KVM process, as well as the number of bytes read from and written to the *hard disk* by the said process. See the [psutil documentation](https://pypi.python.org/pypi/psutil "Psutil documentation") for more info.

## libvirt
Libvirt is responsible for capturing the number of bytes sent and received over all virtual *network interfaces* attached to a KVM guest. In addition to this, libvirt updates the information about the running guests before every data sampling cycle. Such information includes the mapping of process IDs (PIDs) to the KVM domain names, which may vary at any time, e.g. when a new guest enters the system or a running guest is rebooted. The exact PID of a guest process is essential for all data collection tools to always sample the right performance data for the right guest. See the [libvirt homepage](http://libvirt.org/ "Libvirt homepage") for more information.

## perf-stat
Perf-stat is another Linux profiling utility belonging to the Perf toolkit. It is capable of tracking a variety of hardware and software performance counters, depending on their availability on the respective platform.  Examples of counters supported by Perf on the Intel Core i7 architecture are *instructions retired*, *CPU clock*, *cache misses*, or *branch-misses*. Just as with the other tools, process-level performance counters are accessible by supplying the PID of interest to the command. Similar to perf-kvm, perf-stat requires starting and stopping the recording process in order to provide the counter values. The output of Perf-stat is then parsed by the data collector after each sampling interval. See [perf-stat tutorial](https://perf.wiki.kernel.org/index.php/Tutorial#Counting_with_perf_stat "perf-stat tutorial") for more info.
