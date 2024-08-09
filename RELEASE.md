# RELEASE

## 08/08/2024   Version 2.4.3
   * Add reload button in history tab and set shortcut Ctrl+r for reloading/refreshing the plot
   * Update external dependencies
   * Set shortcut Ctrl+q to quit the program
   * Add status bar to history tab

## 05/03/2024   Version 2.4.2
   * Add 14 days to history plot
   * General clean up

## 05/02/2024   Version 2.4
   * Fix facecolor of figure for lHe rec. history plot
   * Optimize pandas read_csv by adding low_memory option
   * Fix history plot issue and change history combo box options
   * Add icon to title bar
   * Performance improvements for plotting history
   * Add feature to sum total lHe recovered in ltrs when user selects start and end dates

## 04/28/2024   Version 2.3  
   * Added splash screen support
   * Added command line option -dl to log the lHe remaining in ltrs in the log file
   * Fix email issue when threshold was updated
   * Add RELEASE.md file

## 01/28/2024   Version 2.2
   * More stringent check to verify that the save lHe remaining value is a number in the save_restore file

## 11/15/2023   Version 2.1
   * Added two new command line options: -t sets the lHe threshold specified by user, -c adds a multipicative correction factor to the He flow (in l/min)
   * Startup option values are saved in log file

## 10/12/2023   Version 2.0
   * save the remaining lHe value (from QLabel) and set it as the start lHe (QLineEdit) on program start up
   * Fix issue with prefix definition in PV

## 08/08/2023   Version 1.94
   * More stringent checks on when to send mail
   * Fix lHe_start_updated() fixed by adding check for email timer active
   * EMAIL_POLL needs to be int 
   * Add multi recepient feature for email in cmd line option
     multiple email addresses need to be seperated by ;

## 07/05/2023   Version 1.91
   * Make LHE_FIN and LHE_LEFT records float
   * Add debug flag to run in debug mode
   * Add location of log directory in About section
   * Revert argparse code
   * Fix NaN issues in code
   * Changed lHe rec plot color to be better visible
   * History plot ignores files that don't end with .txt

## 06/18/2023   Version 1.7
   * Make the program threadsafe
   * Add email feature 

## 06/17/2023   Version 1.6
   * Bug fixes, changed from % to liters to display remaining lHe and setting lHe threshold
   * Added new epics pv's

## 06/15/2023   Version 1.4
  * Handle thread termination more gracefully
  * No longer using QTimer to run the thread to fix GUI freeze issue

## 06/14/2023   Version 1.3
  * Added readback to estimate days before lHe at threshold defined by user

## 06/02/2023   Version 1.21
  * General cleanup, fix some bug

## 05/30/2023   Version 1.2
  * Added calculation to est how much lHe remains in the dewar
  * Added menubar to show information about the program
  * Updated default arguments to not start the pcas server if the PV variable is not set

## 05/25/2023   Version 1.1
  * Added argparse to handle user options/inputs

## 05/22/2023   Version 1.0
  * Added pcas server to broadcast PV data
  * Change He expansion ratio to 754.2
  * Using config files again

## 05/12/2023   Version 0.9
  * Fixed figure background color, using ThreadPoolExwcutor for history plot task

## 05/04/2023   Version 0.8
   * Fixed bug in get_my_data

## 05/02/2023   Version 0.7
   * Added a viewer to look at historic data logged by the bpc, 
   * Added a non-overlapping moving average filter when user selects history >= 1 day so that the live 
     graph does not stall the ui

## 04/17/2023   Version 0.4
   * Added uptime

## 04/13/2023   Version 0.3
   * Remove configparser and config.ini, use env variables for server address
   * Set default server if address not found in environment, reset minute timer in plot after every 24 hrs
   * Change plt axis to show local time, if server rejects connection then close and restart the socket connection
   * Add clear plot button, add plot history option

## 03/28/2023   Version 0.2
   * Fixed issue with exit application when program is running minimized in system tray
   * Remove option to resize or maximize the application
   * Upload to NIST github
   * Prep for creating exe, changed log and data dir to C drive
   * Changed config.ini file location to %USERPROFILE%\\.bpc\\config.ini

## 03/25/2023   Version 0.1
   * First version of the project