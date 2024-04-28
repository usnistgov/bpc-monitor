# README
A program to log data from the back pressure controller of He recovery system in Bldg 218.\
The bpc-monitor records data from a Control pressure, valve status and Gas flow data Vision 130 PLC controller and logs these parameters along with estimating how much lHe is being used by the system connected to the bpc. It is also able to estimate when one needs to refill their system. The program also has a built-in epics pcas server which serves the data as process variables over the network via TCP/UDP broadcasts

## Installation
To install the dependencies just use
```bash
 pip install -r requirements.txt
 ```
 ## Usage
 To run the program with defaults By default save and log directories are created in C:\ drive:
 ```
 C:\__datacache__\
 C:\__logcache__\
 ```
 ```
 python bpc-monitor.py
 ```
 Optionally one can see all the options that this program uses by typing:
 ```
 python bpc-monitor.py -h | more
 ```
 The optional arguments are:
 ```
options:
  -h, --help            show this help message and exit
  -i HOST, --host HOST  specify the host address
  -p PORT, --port PORT  specify the port
  -e EPICS_PV, --epics_pv EPICS_PV
                        Specify the PV epics prefix
  -s SAVE_PATH, --save_path SAVE_PATH
                        Specify data directory
  -l LOG_PATH, --log_path LOG_PATH
                        Specify log directory
  -m MAIL, --mail MAIL  Specify receipients email address
  -d, --debug           Debugging mode
  -t THRESHOLD, --threshold THRESHOLD
                        Specify lHe threshold in ltrs
  -c CORRECTION, --correction CORRECTION
                        Specify correction factor between 1.0 and 2.0
 ```
The repository also contains build scripts to build a local binary using pyinstaller. See bpc-monitor.spec\
Tested on Windows 7, 10, and 11 only.

## Contact
alireza.panna@nist.gov\
frank.seifert@nist.gov