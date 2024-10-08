__author__      =       "Alireza Panna &  Frank Seifert"
__copyright__ 	=       """
                        This data is publicly available according to the NIST statements of copyright, 
                        fair use and licensing; see https://www.nist.gov/director/copyright-fair-use-and-licensing-statements-srd-data-and-software
                        """
__license__ 	=       "NIST"
__maintainer__ 	=       "Alireza Panna"
__email__ 	    =       "alireza.panna@nist.gov"
__status__ 	    =       "Stable"
__date__        =       "03/25/2023"
__version__     =       "2.4.3"

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
                        053023: Added calculation to est how much lHe remains in the dewar, Added menubar to show information about the program, updated default arguments
                                to not start the pcas server if the PV variable is not set update version to 1.2
                        060223: General cleanup, fix some bugs, update to 1.21
                        061423: Various bug-fixes, added readback to estimate days before lHe at threshold defined by user, 
                                update version to 1.3
                        061523: Handle thread termination more gracefully, no longer using QTimer to run the thread to fix GUI freeze issue
                                Update version to 1.4
                        061723: Bug fixes, changed from % to liters to display remaining lHe and setting lHe threshold, added new epics pv's
                        061723: More bug fixes, update to 1.6
                        061823: FIX: make the program threadsafe, add email feature, update to 1.7
                        062623: FIX: make LHE_FIN and LHE_LEFT records float, add debug flag to run in debug mode
                        070223: FIX: Add location of log directory in About section, revert argparse code
                        070523: FIX: NaN issues in code, changed lHe rec plot color to be better visible, history plot ignores files that don't end with .txt, 
                                update to 1.91
                        070723: FIX: More stringent checks on when to send mail
                        080223: FIX: lHe_start_updated() fixed by adding check for email timer active
                        080823: FIX: EMAIL_POLL needs to be int, add multi recepient feature for email in cmd line option. multiple email
                                addresses need to be seperated by ;, update version to 1.94
                        101223: ENH: save the remaining lHe value (from QLabel) and set it as the start lHe (QLineEdit) on program start up. Fix issue with prefix definition 
                                in PV. update version to 2.0
                        111523: ENH: added two new command line options: -t sets the lHe threshold specified by user, -c adds a multipicative correction factor to the He flow (in l/min
                                startup option values are saved in log file.
                        012824: FIX: more stringent check to verify that the save lHe remaining value is a number in the save_restore file.
                        042824: ADD: added splash screen support, added command line option -dl to log the lHe remaining in ltrs in the log file, fix email issue when threshold
                                was updated, update version to 2.3
                        050124: FIX: Facecolor of figure for history plot, fix issue with plotting history data
                        050224: ADD: performance improvements for history plotting, add icon to title bar, add sum feature to get total lHe recovered, update to 2.4
                        072924: MNT: Add 14 days to history plot, clean up, update to 2.4.2
                        080824: ENH: Add reload button in history tab and set shortcut Ctrl+r for reloading/refreshing the plot
                                     Update external dependencies, set shortcut Ctrl+q to quit the program, Add status bar in history tab
                        """