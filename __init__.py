__author__      =       "Alireza Panna &  Frank Seifert"
__copyright__ 	=       "This data is publicly available according to the NIST statements of copyright, fair use and licensing; see https://www.nist.gov/director/copyright-fair-use-and-licensing-statements-srd-data-and-software"
__license__ 	=       "NIST"
__maintainer__ 	=       "Alireza Panna"
__email__ 	=       "alireza.panna@nist.gov"
__status__ 	=       "Stable"
__date__        =       "03/25/2023"
__version__     =       "1.1"

TODO            =
CHANGELOG       =       """
                        032823: Update version string to 0.2
                                Fixed issue with exit application when program is running minimized 
                                in system tray
                                Remove option to resize or maximize the application
                                Upload to NIST github
                                Prep for creating exe, changed log and data dir to C drive
                                Changed config.ini file location to %USERPROFILE%\\.bpc\\config.ini
                        033023: Remove configparser and config.ini, use env variables for server address
                        040223: Set default server if address not found in environment, reset minute timer in plot
                                after every 24 hrs.
                        041323: Change plt axis to show local time, if server rejects connection then close and restart the socket
                                connection, add clear plot button, add plot history option, update version string to 0.3
                        041423: Added uptime 
                        041723: Fixed day calculation in uptime, update version string to 0.4
                        050223: Added a viewer to look at historic data logged by the bpc, added a non-overlapping moving
                                average filter when user selects history >= 1 day so that the live graph does not stall the ui, upgrade to version 0.7.
                        050423: Fixed bug in get_my_data, upgrade to version 0.8
                        051223: Fixed figure background color, using ThreadPoolExwcutor for history plot task, 
                                upgrade to version 0.9
                        052223: Added pcas server to broadcast PV data, change He expansion ratio to 754.2, using config files again, update version to 1.0
                        052523: Added argparse to handle user options/inputs. Update to 1.1
                        """