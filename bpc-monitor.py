#! /usr/bin/env python
import sys, os

try:
    print("Using PyQt6...")
    os.environ["QT_API"] = "pyqt6"
    from PyQt6 import QtCore, uic, QtGui
    from PyQt6.QtCore import pyqtSignal, QTimer, QThread, QSettings, QObject
    from PyQt6.QtWidgets import QApplication, QMainWindow, QSystemTrayIcon, QStyle, QMenu, QMessageBox
    from PyQt6.QtGui import QAction
    pixmapi = QStyle.StandardPixmap.SP_TitleBarMenuButton
except ImportError:
    print("Using PyQt5...")
    os.environ["QT_API"] = "pyqt5"
    from PyQt5 import QtCore, uic, QtGui
    from PyQt5.QtCore import pyqtSignal, QTimer, QThread, QSettings, QObject
    from PyQt5.QtWidgets import QApplication, QMainWindow, QSystemTrayIcon, QStyle, QAction, QMenu, QMessageBox
    pixmapi = QStyle.SP_TitleBarMenuButton

import pyqtgraph as pg
from collections import deque
import time, datetime
import inspect, signal
import Vision130

#try:
#    from configparser import ConfigParser
#except ImportError:
#    from ConfigParser import ConfigParser  # ver. < 3.0
import logging
from logging.handlers import TimedRotatingFileHandler

# base directory of the project
if getattr(sys, 'frozen', False):
    # PyInstaller creates a temp folder and stores path in _MEIPASS
    base_dir = sys._MEIPASS
    # base_dir = os.path.dirname(sys.executable)
    running_mode = 'Frozen/executable'
else:
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        running_mode = "Non-interactive (e.g. 'python bpc-monitor.py')"
    except NameError:
        base_dir = os.getcwd()
        running_mode = 'Interactive'

datadir   = "C:" + os.sep + "_datacache_"
logdir    = "C:" + os.sep + "_logcache_"
#configdir = os.environ.get('USERPROFILE') + '\\.bpc'
# create a folder to store data and log files
if os.path.isdir(datadir) == False:
    os.mkdir(datadir)  
if os.path.isdir(logdir) == False:
    os.mkdir(logdir)
#if os.path.isdir(configdir) == False:
#    try:
#        os.mkdir(configdir)
#        f = open(configdir + os.sep + "config.ini", 'x')
#        f.write('[vision130]\n')
#        f.write('host: ' + '172.30.33.212'+ '\n') # example ip
#        f.write('port: ' + '20256' + '\n') # example port
#        f.close()
#    except:
#        pass

# Create the logger
logger = logging.getLogger(__name__)
# set the log level
logger.setLevel(logging.INFO)
# define the file handler and formatting
lfname = logdir + os.sep + 'bpc-monitor' + '.log'
file_handler = TimedRotatingFileHandler(lfname, when='midnight')
fmt = logging.Formatter('%(asctime)s : %(levelname)s : %(name)s : %(message)s')
file_handler.setFormatter(fmt)
logger.addHandler(file_handler)

__version__ = "0.3" # Program version string
MAIN_THREAD_POLL = 1000 # in ms
He_EXP_RATIO = 1./757 # liquid to gas expansion ratio for Helium at RT
WIDTH = 410
HEIGHT= 270
HIST = 24
os.chdir(base_dir)
# load the main ui file
main_file = uic.loadUiType(os.path.join(base_dir, 'ui\\main.ui'))[0]

class mainThread(QThread, QObject):
    # define the signals that this thread calls
    update_data = pyqtSignal(list)
    plot_temp = pyqtSignal()

    def __init__(self):
        """
        Constructor for the main thread
        """
        logger.info("In function: " + inspect.stack()[0][3])
        QtCore.QThread.__init__(self)
        QtCore.QObject.__init__(self)
        self.setTerminationEnabled(True)

    def __del__(self):
        """
        Destructor for the main thread, handles thread termination
        """
        self.wait()
        logger.info("In function: " + inspect.stack()[0][3])

    def _getRbvs(self,):
        logger.info("In function: " + inspect.stack()[0][3])
        try:
            bpc_rbv =  mybpc.get_all_float() # get all float data from the controller
            return bpc_rbv
        except Exception as e:
            logger.info("In function: " + inspect.stack()[0][3] + ' ' + str(e))
            return [0]*24
        

    def run(self):
        """
        Main thread processing loop
        - emits various signals to update or poll data from devices
        - This function is called every 1 s, this can be changed by setting
          MAIN_THREAD_POLL
        """
        try:
            logger.info("In function: " + inspect.stack()[0][3])
            all_rbv = self._getRbvs()
            # print (all_rbv)
            self.update_data.emit(all_rbv)
            self.plot_temp.emit()
        except Exception as e:
            logger.info("In function: " +  inspect.stack()[0][3] + " Exception: " + str(e))
            pass

    def stop(self):
        """
        Stops the main thread
        """
        logger.info("In function: " + inspect.stack()[0][3])
        file_handler.close()
        self.quit()

class mainWindow(QMainWindow, main_file):

    def __init__(self):
        QMainWindow.__init__(self)
        self.setFixedSize(WIDTH, HEIGHT)
        self.tray_icon = None
        self.quit_flag = 0
        # self.ct = 0
        self.timestamp = datetime.datetime.now()
        self.settings = QSettings("global_settings.ini", QSettings.Format.IniFormat)
        self.setupUi(self)
        self.timer = QTimer()
        self.plot_settings()
        self.fname = datadir + '\\bpc_log_' + time.strftime("%Y%m%d") + '.txt'
        self.data_pressure = deque(maxlen=int(86400/(HIST*MAIN_THREAD_POLL*1e-3))) # 
        self.data_flow = deque(maxlen=int(86400/(HIST*MAIN_THREAD_POLL*1e-3)))

        mthread.update_data.connect(self._getAllData)
        mthread.plot_temp.connect(self.plot_data)

        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(pixmapi))

        show_action = QAction("Show BPC logger", self)
        quit_action = QAction("Exit", self)
        hide_action = QAction("Hide BPC logger", self)

        tray_menu = QMenu()
        tray_menu.addAction(show_action)
        tray_menu.addAction(hide_action)
        tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

        self.btn_quit.clicked.connect(self.quit)
        self.btn_clr_plots.clicked.connect(self.clear_plots)
        show_action.triggered.connect(self.show)
        quit_action.triggered.connect(self._exit_app)
        hide_action.triggered.connect(self.hide)
        
        self.cb_plt_hist.addItems(['1 min', '5 min', '1 hr', '2 hr', '12 hr', '1 d', '2 d', '1 w'])
        self.cb_plt_hist.setCurrentText('1 hr')
        self.cb_plt_hist.activated.connect(self.set_plot_history)
        
        logger.info ("In function: " + inspect.stack()[0][3])
        self.start_time = time.time()

    def show(self):
        """
        Show the main window and connect to signals coming from various threads
        """
        logger.info("In function: " + inspect.stack()[0][3])
        QMainWindow.show(self)
        self.timer.timeout.connect(self.checkMainThread)
        # run the main thread every 1s
        self.timer.start(MAIN_THREAD_POLL)

    def _exit_app(self):
        """
        Helper function to exit from system tray
        """
        logger.info("In function: " + inspect.stack()[0][3])
        self.quit_flag = 1
        self.quit()

    def _getAllData(self, all_rbv):
         # print(all_rbv)
         self.timestamp = datetime.datetime.now()
         self.lbl_pressure_rbv.setText(str(round(all_rbv[20], 3)))
         self.lbl_flow_rbv.setText(str(round(all_rbv[10], 3)))
         self.lbl_valve_rbv.setText(str(round(all_rbv[-1], 3)))
         rec = round(all_rbv[10]*60*24/(1/He_EXP_RATIO), 3)
         self.lbl_rec_rbv.setText(str(rec))

    def checkMainThread(self):
        """
        A QTimer is used to run the main thread every 1 s.
        We also use this to update the filename of the data file
        """
        try:
            up = datetime.timedelta(seconds=(time.time() - self.start_time))
            days = int((up.days))
            print (up, up.seconds, up.days)
            hours = int((up.seconds/3600)%24)
            mins = int((up.seconds/60)%60)
            secs = int(up.seconds%60)
            #print (days, hours, mins, secs)
            self.le_uptime.setText(str(days) + 'd, ' + str(hours) + \
                                  ':' + str(mins) + ':' + str(secs))
            if not mthread.isRunning():
                logger.info("In function: " + inspect.stack()[0][3])
                mthread.start()
        except KeyboardInterrupt:
            if mthread.isRunning():
                mthread.stop()
            file_handler.close()
            self.close()
        self.fname = datadir + '\\bpc_log_' + time.strftime("%Y%m%d") + '.txt'
    
    def set_plot_history(self):
        plt_history = self.cb_plt_hist.currentText()
        if plt_history == '1 min':
            HIST = 1440
        elif plt_history == '5 min':
            HIST = 288
        elif plt_history == '1 hr':
            HIST = 24
        elif plt_history == '2 hr':
            HIST = 12
        elif plt_history == '12 hr':
            HIST = 2
        elif plt_history == '1 d':
            HIST = 1
        elif plt_history == '2 d':
            HIST = 0.5
        elif plt_history == '1 w':
            HIST = 0.143
        self.data_pressure = deque(maxlen=int(86400/(HIST*MAIN_THREAD_POLL*1e-3)))
        self.data_flow = deque(maxlen=int(86400/(HIST*MAIN_THREAD_POLL*1e-3)))
        
    def clear_plots(self):
        logger.info("In function: " + inspect.stack()[0][3])
        try:
            # clear/redefine the tuples
            self.data_pressure = deque(maxlen=int(86400/(HIST*MAIN_THREAD_POLL*1e-3)))
            self.data_flow = deque(maxlen=int(86400/(HIST*MAIN_THREAD_POLL*1e-3)))
        except Exception as e:
            logger.info("In function: " +  inspect.stack()[0][3] + " Exception: " + str(e))

    def plot_settings(self):
        """
        Initial settings for plot items
        """
        logger.info("In function: " + inspect.stack()[0][3])
        labelStyle_y1 = {'color': 'red', 'font-size': '8pt'}
        labelStyle_y2 = {'color': 'blue', 'font-size': '8pt'}
        labelStyle_x = {'color': 'black', 'font-size': '8pt'}
        self.pw.plotItem.clear()
        self.pw_2.plotItem.clear()
        self.pw.setBackground((0,0,0,240))
        self.pw_2.setBackground((0,0,0,240))
        self.pw.plotItem.setLabel(axis='left', text='P', units= 'mbar', **labelStyle_y1)
        self.pw_2.plotItem.setLabel(axis='left', text='Flow', units= 'l/min',  **labelStyle_y2)
        self.pw_2.plotItem.setLabel(axis='bottom', text = 'time', units= 'HH:MM:SS', **labelStyle_x)
        self.pw.plotItem.showGrid(x=True, y=False)
        self.pw_2.plotItem.showGrid(x=True, y=False)
        date_axis = pg.DateAxisItem()
        self.pw_2.setAxisItems({'bottom': date_axis})
        item = self.pw.getPlotItem()
        item_2 = self.pw_2.getPlotItem()
        item.hideAxis('bottom')
        # self.xax = item.getAxis('bottom')
        # self.xax.enableAutoSIPrefix(enable=False)
        self.xax_2 = item_2.getAxis('bottom')
        self.xax_2.enableAutoSIPrefix(enable=False)
        self.yax = item.getAxis('left')
        self.yax.enableAutoSIPrefix(enable=False)
        self.yax_2 = item.getAxis('left')
        self.yax_2.enableAutoSIPrefix(enable=False)
        self.curve1 = self.pw.plot()
        self.curve2 = self.pw_2.plot()

    @QtCore.pyqtSlot()
    def plot_data(self):

        logger.info("In function: " + inspect.stack()[0][3])
        # convert datetime object to timestamp
        ct = self.timestamp.timestamp()
        pressure = self.lbl_pressure_rbv.text()
        flow = self.lbl_flow_rbv.text()
        valve = self.lbl_valve_rbv.text()

        if pressure != '0':
            self.data_pressure.append({'x':ct, 'y':float(pressure),})
            self.data_flow.append({'x':ct, 'y':float(flow),})
            # append the data to file
            with open(self.fname, 'a') as f:
                f.write(str(self.timestamp) + '\t' + str(pressure) + '\t' + str(flow) + '\t' + str(valve) + '\n')
        count_list = [item['x'] for item in self.data_pressure]
        count_list_2 = [item['x'] for item in self.data_flow]
        pressure_list = [item['y'] for item in self.data_pressure]
        flow_list = [item['y'] for item in self.data_flow]
        #print (len(self.data_pressure), len(self.data_flow))
        try:
            self.curve1.setData(x = count_list, y = pressure_list, pen = 'r', shadowPen = 'r', symbol='o', symbolSize=1.5, symbolBrush='r')
            self.curve2.setData(x = count_list_2, y = flow_list, pen = 'b', shadowPen = 'b', symbol='x', symbolSize=1.5, symbolBrush='b')
        except:
            self.curve1.setData(x = count_list, y = 0.00, pen = 'r', symbol='o', symbolSize=1.5, symbolBrush='r')
            self.curve2.setData(x = count_list_2, y = 0.00, pen = 'b', symbol='x', symbolSize=1.5, symbolBrush='b')

    def closeEvent(self, event):
        """
        Handle 'X' event to minimize to system icon tray instead of closing
        Override the close event to minimize to system tray
        """
        logger.info("In function: " + inspect.stack()[0][3])
        if self.quit_flag == 0:
            self.hide()
            self.tray_icon.showMessage(
                "BPC Monitor",
                "Application was minimized to tray",
                QSystemTrayIcon.MessageIcon.Information,
                1000
            )
            event.ignore()
        if self.quit_flag == 1:
            self.tray_icon.showMessage(
                "BPC Monitor",
                "Terminating the application",
                QSystemTrayIcon.MessageIcon.Information,
                1000
            )
            self.tray_icon.hide()
            del self.tray_icon
            self.quit()
            event.accept()

    def quit(self):
        """
        Quit the application
        """
        logger.info("In function: " + inspect.stack()[0][3])
        if self.quit_flag == 0:
            reply = QMessageBox.question(
            self, "Message",
            "Are you sure you want to quit?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes)
            if reply == QMessageBox.StandardButton.Yes:
                self.quit_flag = 1
                mybpc.close_comm()
                self.close()
                QtCore.QCoreApplication.instance().quit
                app.quit()
            else:
                pass
        if self.quit_flag == 1:
            mybpc.close_comm()
            self.close()
            QtCore.QCoreApplication.instance().quit
            app.quit()

#################################################################################################
def _sigint_handler(*args):
    """
    Handler for the SIGINT signal. For testing purposes only
    """
    sys.stderr.write('\r')
    if QMessageBox.question(None, '', "Are you sure you want to quit?",
                                  QtGui.QMessageBox.Yes | QtGui.QMessageBox.No,
                                  QtGui.QMessageBox.No) == QtGui.QMessageBox.Yes:

        mthread.stop()
        mainWindow.loop.close()
        QtGui.QApplication.quit()

if __name__ == '__main__':
    # Handle high resolution displays:
    if hasattr(QtCore.Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    if hasattr(QtCore.Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)
    # Create the Qt application
    app = QApplication(sys.argv)
    # read the .ini file
    #config = ConfigParser()
    #user_config = configdir + os.sep + 'config.ini'
    #if os.path.exists(user_config) and os.path.isfile(user_config):
    #    config_path = user_config
    #else:
    #    config_path = os.getcwd() + os.sep + 'config.ini'
    #config.read(config_path)
    # Initialize all the hardware used for this application
    try:
        myserver = str(os.getenv('BPC_SERVER'))
    except:
        myserver = '172.30.33.212'
    mybpc = Vision130.Vision130Driver(myserver, '20256')
    # start the main thread
    mthread = mainThread()
    mthread.start()
    # Create the main window
    main_window = mainWindow()
    # Remove the title bar and set to fixed geometry to match our touch screen display
    # main_window.setWindowFlags(QtCore.Qt.FramelessWindowHint)
    main_window.setGeometry(500, 500, WIDTH, HEIGHT)
    # Set the program version
    main_window.setWindowTitle("BPC Logger " + __version__)
    main_window.show()
    # handle ctrl+c event
    signal.signal(signal.SIGINT, _sigint_handler)
    # Start the GUI thread
    sys.exit(app.exec())
