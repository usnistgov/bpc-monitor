#! /usr/bin/env python
import sys
from os import getenv, environ, chdir, sep, path, mkdir, getcwd, scandir
try:
    environ["QT_API"] = "pyqt6"
    from PyQt6 import QtCore, uic, QtGui
    from PyQt6.QtCore import pyqtSignal, QTimer, QThread, QSettings, QObject
    from PyQt6.QtGui import QAction
    from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,\
                                QLabel, QPushButton, QComboBox,\
                                QMessageBox, QMenu, QSystemTrayIcon, QStyle, QTabWidget,
                                QFormLayout)
    pixmapi = QStyle.StandardPixmap.SP_TitleBarMenuButton
except ImportError:
    environ["QT_API"] = "pyqt5"
    from PyQt5 import QtCore, uic, QtGui
    from PyQt5.QtCore import pyqtSignal, QTimer, QThread, QSettings, QObject
    from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,\
                                QLabel, QPushButton, QComboBox, \
                                QMessageBox, QSystemTrayIcon, QStyle, QMenu, QAction, QTabWidget,
                                QFormLayout)
    pixmapi = QStyle.SP_TitleBarMenuButton

import pyqtgraph as pg
from collections import deque
from datetime import datetime, timedelta
from time import strftime, time, perf_counter
import inspect, signal
# controller class
import Vision130
from numpy import NaN, mean, array
# matplotlib imports
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib
from matplotlib.dates import ConciseDateFormatter, AutoDateLocator
import matplotlib.style as mplstyle
import matplotlib.pyplot as plt
from concurrent.futures import ThreadPoolExecutor

from pandas import read_csv, concat, to_datetime
#try:
#    from configparser import ConfigParser
#except ImportError:
#    from ConfigParser import ConfigParser  # ver. < 3.0
# for logging
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
        base_dir = getcwd()
        running_mode = 'Interactive'

# directories to store data from the controller and program logs
datadir   = "C:" + sep + "_datacache_"
logdir    = "C:" + sep + "_logcache_"
#configdir = os.environ.get('USERPROFILE') + '\\.bpc'
# create a folder to store data and log files
if path.isdir(datadir) == False:
    mkdir(datadir)
if path.isdir(logdir) == False:
    mkdir(logdir)
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
lfname = logdir + sep + 'bpc-monitor' + '.log'
file_handler = TimedRotatingFileHandler(lfname, when='midnight')
fmt = logging.Formatter('%(asctime)s : %(levelname)s : %(name)s : %(message)s')
file_handler.setFormatter(fmt)
logger.addHandler(file_handler)

# python globals
__version__ = '0.9' # Program version string
MAIN_THREAD_POLL = 1000 # in ms
He_EXP_RATIO = 1./757 # liquid to gas expansion ratio for Helium at RT
WIDTH = 420
HEIGHT= 310
HIST = 24
WORKERS = 8

chdir(base_dir)
# load the main ui file
main_file = uic.loadUiType(path.join(base_dir, 'ui\\main.ui'))[0]
mplstyle.use('fast')

params = {
           'axes.labelsize': 5,
           'font.size': 5,
           'xtick.labelsize': 5,
           'ytick.labelsize': 6,
           'text.usetex': False,
           'figure.figsize': [5,2],
           'figure.max_open_warning': 20,
           'figure.facecolor': '#f0f0f0',
           'figure.edgecolor': 'white',
           'figure.dpi': 100,
           'axes.spines.top': True,
           'axes.spines.bottom': True,
           'axes.spines.left': True,
           'axes.spines.right': True,
           'axes.linewidth': 1.2,
           'lines.linewidth': 1.0,
           'lines.markersize': 1.0,
           'grid.color': 'gray',
           'grid.linestyle': '-',
           'grid.alpha': 0.6,
           'grid.linewidth': 0.8,
           'axes.formatter.use_mathtext' : True,
           'legend.loc': 'best',
           'legend.frameon': False,
           'legend.fontsize': 5,
           'markers.fillstyle': 'none',
           'xtick.direction':   'in',     # direction: {in, out, inout}
           'ytick.direction':   'in',     # direction: {in, out, inout}
           'savefig.dpi': 300,
           'figure.raise_window' : True
          }

plt.rc('font', family = 'serif')
matplotlib.rcParams.update(params)

class MplCanvas(FigureCanvasQTAgg):

    def __init__(self, parent=None, width=5, height=2, dpi=180):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.ax1 = self.fig.add_subplot(111)
        self.ax_settings()
        super(MplCanvas, self).__init__(self.fig)

    def ax_settings(self, ):
        #logger.info ('In function: ' + inspect.stack()[0][3])
        locator =   AutoDateLocator(minticks=5, maxticks=5)
        date_form = ConciseDateFormatter(locator)
        self.ax1.xaxis.set_major_formatter(date_form)
        self.ax1.tick_params(axis='x', labelrotation = 45)
        self.ax1.set_ylabel('lHe rec. (l/day)')
        self.ax1.set_xlabel('Date')
        self.fig.canvas.draw()
        # self.fig.tight_layout(pad=0.4, w_pad=1, h_pad=1.0)

class mainThread(QThread, QObject):
    # define the signals that this thread calls
    update_data = pyqtSignal(list)
    plot_temp = pyqtSignal()

    def __init__(self):
        """
        Constructor for the main thread
        """
        #logger.info("In function: " + inspect.stack()[0][3])
        QtCore.QThread.__init__(self)
        QtCore.QObject.__init__(self)
        self.setTerminationEnabled(True)

    def __del__(self):
        """
        Destructor for the main thread, handles thread termination
        """
        self.wait()
        #logger.info("In function: " + inspect.stack()[0][3])

    def _getRbvs(self,):
        #logger.info("In function: " + inspect.stack()[0][3])
        try:
            bpc_rbv =  mybpc.get_all_float() # get all float data from the controller
            return bpc_rbv
        except Exception as e:
            logger.info("In function: " + inspect.stack()[0][3] + ' ' + str(e))
            return [NaN]*24

    def run(self):
        """
        Main thread processing loop
        - emits various signals to update or poll data from devices
        - This function is called every 1 s, this can be changed by setting
          MAIN_THREAD_POLL
        """
        try:
            #logger.info("In function: " + inspect.stack()[0][3])
            all_rbv = self._getRbvs()
            #print (all_rbv)
            self.update_data.emit(all_rbv)
            self.plot_temp.emit()
        except Exception as e:
            self.update_data.emit(all_rbv)
            logger.info("In function: " +  inspect.stack()[0][3] + " Exception: " + str(e))
            pass

    def stop(self):
        """
        Stops the main thread
        """
        #logger.info("In function: " + inspect.stack()[0][3])
        file_handler.close()
        self.quit()

class mainWindow(QTabWidget, main_file):

    def __init__(self):
        global HIST
        global MAIN_THREAD_POLL
        QTabWidget.__init__(self)
        # self.tab1 = QWidget()
        self.tab2 = QWidget()
        self.addTab(self.tab2,"History")
        # self.addTab(self.tab1, "Logger")
        self.sc = MplCanvas(self, width=5, height=2, dpi=180)
        # self.tab1UI()
        self.tab2UI()
        self.setFixedSize(WIDTH, HEIGHT)
        self.tray_icon = None
        # program flags 
        self.quit_flag = 0
        self.draw_bpc_flag = 0
        self.timestamp = datetime.now()
        self.settings = QSettings("global_settings.ini", QSettings.Format.IniFormat)
        self.setupUi(self)
        self.timer = QTimer()
        self.plot_settings()
        self.fname = datadir + '\\bpc_log_' + strftime("%Y%m%d") + '.txt'
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

        self.cb_plt_hist.addItems(['1 min', '5 min', '1 hr', '2 hr', '12 hr', '1 d', '2 d', '1 w', '1 m', '1 y'])
        self.cb_plt_hist.setCurrentText('1 hr')
        self.cb_plt_hist.activated.connect(self.set_plot_history)
        self.plt_history = self.cb_plt_hist.currentText()

        #logger.info ("In function: " + inspect.stack()[0][3])
        self.start_time = time()
        
    def tab1UI(self, ):
        """
        not used
        """
        layout = QFormLayout()
        self.lbl_pressure = QLabel('P [mbar]')
        self.lbl_pressure_rbv = QLabel()
        
        layout.addWidget(self.lbl_pressure)
        layout.addWidget(self.lbl_pressure_rbv)
        self.tab1.setLayout(layout)

    def tab2UI(self, ):
        layout = QVBoxLayout()
        layout2 = QHBoxLayout()
        toolbar = NavigationToolbar(self.sc, self)
        self.lbl_time = QLabel('HISTORY: ')
        self.cb_time = QComboBox()
        self.cb_time.addItems(['last 48 hrs', 'last week', \
                               'last month', 'last six months', 'last year', \
                               'all'])
        self.cb_time.setCurrentText('last 48 hrs')
        self.cb_time.setFixedWidth(100)
        self.cb_time.setFixedHeight(20)

        # combo box to resample data
        self.lbl_resample = QLabel('BINNING: ')
        self.lbl_resample.setFixedHeight(40)
        self.cb_resample = QComboBox()
        self.cb_resample.addItems(['1S', '10S', '30S', '1min', '30min', '1H', \
                                   '2H', '12H', '1D', '1W', '2W', '1M'])
        self.cb_resample.setCurrentText('1min')
        self.cb_resample.setFixedHeight(20)
        self.cb_resample.setFixedWidth(60)
        self.binsize = self.cb_resample.currentText()

        self.btn_plot = QPushButton('PLOT', self)
        self.btn_plot.setToolTip('Plot/Re-plot the data')
        self.btn_plot.setFixedHeight(20)
        self.btn_plot.setFixedWidth(100)
        self.btn_plot.clicked.connect(self.plot_my_data)

        layout2.addWidget(self.lbl_time)
        layout2.addWidget(self.cb_time)
        layout2.addWidget(self.lbl_resample)
        layout2.addWidget(self.cb_resample)
        layout2.addWidget(self.btn_plot)
        layout2.addStretch(1)
        layout.addWidget(toolbar)
        layout.addLayout(layout2)
        layout.addWidget(self.sc)
        self.tab2.setLayout(layout)

    def plot_my_data(self,):
        #logger.info("In function: " + inspect.stack()[0][3])
        self.btn_plot.setEnabled(False)
        try:
            #print ("In plot_my_data")
            with ThreadPoolExecutor(max_workers=WORKERS) as executor:
                self.df_bpcCtrl = (executor.submit(self.get_my_data))
            self.df_bpcCtrl = self.df_bpcCtrl.result()
            self.redraw()
        except Exception as e:
            logger.info("In function: " +  inspect.stack()[0][3] + "Exception: " + str(e))
            pass
        self.btn_plot.setEnabled(True)

    def _read_helper(self, filename,):
        """
        helper function for get_data
        """
        try:
            mydata = []
            headers = ['Date', 'Pressure', 'Flow', 'Valve']
            mydata.append(read_csv(filename, sep='\t', dtype={0:"str", 1: "float16", 2:"float16", 3:"float16"}, \
                                          on_bad_lines='skip', na_filter=True, index_col=False, memory_map=True, \
                                          usecols=[0,1,2,3], engine='c', names=headers, na_values='nan'))
            return mydata
        except Exception as e:
            logger.info("In function: " +  inspect.stack()[0][3] + "In file: ", str(filename) + " Exception: " + str(e))

    #@functools.lru_cache(maxsize=128)
    def get_my_data(self,):
        global datadir
        mydata = []
        data   = []
        get_data_start = perf_counter()
        try:
            #print ("In get_my_data")
            i = 0
            for filename in scandir(datadir + '\\'):
                self.filename = filename.name
                
                if filename.name != '':
                    if self.cb_time.currentText() == 'all':
                        mydata.append(self._read_helper(datadir + sep + filename.name))

                    elif self.cb_time.currentText() == 'last year':
                        fname_date = datetime.strptime((((filename.name.split('.')[0])).split('_')[-1]), "%Y%m%d")
                        delta_time = (datetime.now() - fname_date).total_seconds()
                        if (float(delta_time) <= 3.1556952*1e7):
                            mydata.append(self._read_helper(datadir + sep + filename.name))

                    elif self.cb_time.currentText() == 'last six months':
                        fname_date = datetime.strptime((((filename.name.split('.')[0])).split('_')[-1]), "%Y%m%d")
                        delta_time = (datetime.now() - fname_date).total_seconds()
                        if (float(delta_time) <= 1.578*1e7):
                            mydata.append(self._read_helper(datadir + sep + filename.name))
                            #print (filename.name, mydata)
                    elif self.cb_time.currentText() == 'last month':
                        fname_date = datetime.strptime((((filename.name.split('.')[0])).split('_')[-1]), "%Y%m%d")
                        delta_time = (datetime.now() - fname_date).total_seconds()
                        if (float(delta_time) <= 2.63*1e6):
                            mydata.append(self._read_helper(datadir + sep + filename.name))
                            #print (filename.name, mydata)
                    elif self.cb_time.currentText() == 'last week':
                        fname_date = datetime.strptime((((filename.name.split('.')[0])).split('_')[-1]), "%Y%m%d")
                        delta_time = (datetime.now() - fname_date).total_seconds()
                        if (float(delta_time) <= 604800):
                            mydata.append(self._read_helper(datadir + sep + filename.name))

                    elif self.cb_time.currentText() == 'last 48 hrs':
                        fname_date = datetime.strptime((((filename.name.split('.')[0])).split('_')[-1]), "%Y%m%d")
                        delta_time = (datetime.now() - fname_date).total_seconds()
                        if (float(delta_time) <= 172800):
                            mydata.append(self._read_helper(datadir + sep + filename.name))

                    else:
                        mydata.append(self._read_helper(datadir + sep + filename.name))
        except:
            logger.info('Error reading file/getting data in filename: ' + str(self.filename) + ' ' + str(inspect.stack()[0][3]))
            pass
        if mydata != []:
            for i in mydata:
                data.extend(i)
        else:
            logger.info("Empty dataset")
            return
        self.binsize = self.cb_resample.currentText()
        dfc = concat(data, ignore_index=True)
        dfc['Date'] = to_datetime(dfc['Date'])
        dfc.insert(4, "lHe Rec.", dfc['Flow']*60*24/(1./He_EXP_RATIO))
        dfc.set_index('Date', inplace=True)
        # print (dfc.head(5))
        resample_dfc = dfc.resample(self.binsize, axis=0, closed='left', label='left').mean()
        resample_dfc.dropna(axis=0, inplace=True)
        resample_dfc['Date'] = resample_dfc.index
        get_data_end = perf_counter() - get_data_start
        logger.info("Time taken to get and analyze data: " +  str(get_data_end))
        return (resample_dfc)

    def redraw(self,):
        try:
            redraw_start = perf_counter()
            self.plot_history_data()
            self.sc.flush_events()
            self.sc.draw_idle()
            self.sc.fig.tight_layout()
            logger.info('Time taken plot the data and draw canvas: ' + \
                        str(perf_counter() - redraw_start) + '\n')
        except:
            logger.info("Error in function: " + str(inspect.stack()[0][3]))
            pass

    def plot_history_data(self, ):
        #logger.info ('In function: ' + inspect.stack()[0][3])
        try:
            if self.draw_bpc_flag == 1:
                self.plot1_ref[0].set_data(self.df_bpcCtrl['Date'], self.df_bpcCtrl['lHe Rec.'])
            else:
                self.plot1_ref = self.sc.ax1.plot(self.df_bpcCtrl['Date'], self.df_bpcCtrl['lHe Rec.'], ms=0.2, \
                                                  c='green', alpha=0.7, marker='o', ls='', label='')
                # self.sc.ax1.legend(loc = 'upper right', frameon=True)
            self.draw_bpc_flag = 1

        except Exception as e:
            logger.info('Error in function: ' + inspect.stack()[0][3] + ' ' + str(e))
            if self.plot1_ref != None:
                self.plot1_ref[0].remove()
                self.plot1_ref = None
            self.draw_bpc_flag = 0
            pass
        self.sc.ax1.relim()
        self.sc.ax1.autoscale(tight=None, axis='both', enable=True)
        self.sc.ax1.autoscale_view(tight=None, scalex=True, scaley=True)

    def show(self):
        """
        Show the main window and connect to signals coming from various threads
        """
        global MAIN_THREAD_POLL
        #logger.info("In function: " + inspect.stack()[0][3])
        QMainWindow.show(self)
        self.sc.fig.tight_layout()
        # self.timer.setTimerType(QtCore.Qt.PreciseTimer)
        self.timer.timeout.connect(self.check_worker_thread)
        # run the main thread every 1s
        self.timer.start(MAIN_THREAD_POLL)

    def _exit_app(self):
        """
        Helper function to exit from system tray
        """
        #logger.info("In function: " + inspect.stack()[0][3])
        self.quit_flag = 1
        self.quit()

    def _getAllData(self, all_rbv):
         # print(all_rbv)
         self.timestamp = datetime.now()
         self.lbl_pressure_rbv.setText(str(round(all_rbv[20], 3)))
         self.lbl_flow_rbv.setText(str(round(all_rbv[10], 3)))
         self.lbl_valve_rbv.setText(str(round(all_rbv[-1], 3)))
         rec = round(all_rbv[10]*60*24/(1./He_EXP_RATIO), 3)
         self.lbl_rec_rbv.setText(str(rec))

    def check_worker_thread(self):
        """
        A QTimer is used to run the main thread every 1 s.
        We also use this to update the filename of the data file
        """
        try:
            up = timedelta(seconds=(time() - self.start_time))
            days = int((up.days))
            hours = int((up.seconds/3600)%24)
            mins = int((up.seconds/60)%60)
            secs = int(up.seconds%60)
            #print (days, hours, mins, secs)
            self.le_uptime.setText(str(days) + 'd, ' + str(hours) + \
                                  ':' + str(mins) + ':' + str(secs))
            if not mthread.isRunning():
                #logger.info("In function: " + inspect.stack()[0][3])
                mthread.start()
        except Exception as e:
            logger.info("In function: " +  inspect.stack()[0][3] + " Exception: " + str(e))
            if mthread.isRunning():
                mthread.stop()
            file_handler.close()
            self.close()
        self.fname = datadir + '\\bpc_log_' + strftime("%Y%m%d") + '.txt'

    def set_plot_history(self):
        global HIST
        global MAIN_THREAD_POLL
        self.plt_history = self.cb_plt_hist.currentText()
        if self.plt_history == '1 min':
            HIST = 1440
        elif self.plt_history == '5 min':
            HIST = 288
        elif self.plt_history == '1 hr':
            HIST = 24
        elif self.plt_history == '2 hr':
            HIST = 12
        elif self.plt_history == '12 hr':
            HIST = 2
        elif self.plt_history == '1 d':
            HIST = 2
        elif self.plt_history == '2 d':
            HIST = 2
        elif self.plt_history == '1 w':
            HIST = 2
        elif self.plt_history == ' 1 m':
            HIST = 2
        elif self.plt_history == ' 1 y':
            HIST = 2
        self.data_pressure = deque(maxlen=int(86400/(HIST*MAIN_THREAD_POLL*1e-3)))
        self.data_flow = deque(maxlen=int(86400/(HIST*MAIN_THREAD_POLL*1e-3)))

    def clear_plots(self):
        global HIST
        global MAIN_THREAD_POLL
        #logger.info("In function: " + inspect.stack()[0][3])
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
        #logger.info("In function: " + inspect.stack()[0][3])
        labelStyle_y1 = {'color': 'red', 'font-size': '8pt'}
        labelStyle_y2 = {'color': 'blue', 'font-size': '8pt'}
        labelStyle_x = {'color': 'black', 'font-size': '8pt'}
        self.pw.plotItem.clear()
        self.pw_2.plotItem.clear()
        self.pw.setBackground((0,0,0,240))
        self.pw_2.setBackground((0,0,0,240))
        self.pw.plotItem.setLabel(axis='left', text='P', units= 'mbar', **labelStyle_y1)
        self.pw_2.plotItem.setLabel(axis='left', text='lHe Rec.', units= 'l/day',  **labelStyle_y2)
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

    def _average(self, arr, n):
        n = int(n)
        binned = []
        co=0
        if len(arr) == 1:
            return (arr)
        while co < len(arr):
            binned.append(mean(arr[co:co+n]))
            co = co+n
        return(binned)

    @QtCore.pyqtSlot()
    def plot_data(self):
        global HIST
        #logger.info("In function: " + inspect.stack()[0][3])
        # convert datetime object to timestamp
        ct = self.timestamp.timestamp()
        pressure = self.lbl_pressure_rbv.text()
        flow = self.lbl_flow_rbv.text()
        rec = self.lbl_rec_rbv.text()
        valve = self.lbl_valve_rbv.text()

        if pressure != '0':
            self.data_pressure.append({'x':ct, 'y':float(pressure),})
            self.data_flow.append({'x':ct, 'y':float(rec),})
            with open(self.fname, 'a') as f:
                if str(pressure) != 'nan':
                    f.write(str(self.timestamp) + '\t' + str(pressure) + '\t' + str(flow) + '\t' + str(valve) + '\n')
        ct_list = [item['x'] for item in self.data_flow]
        pressure_list = [item['y'] for item in self.data_pressure]
        flow_list = [item['y'] for item in self.data_flow]
        # print ('before: ', len(pressure_list))
        if self.plt_history == '1 d':
            ct_list = self._average(array(ct_list), HIST)
            pressure_list = self._average(array(pressure_list), HIST)
            flow_list = self._average(array(flow_list), HIST)
        if self.plt_history == '2 d':
            ct_list = self._average(array(ct_list), 2*HIST)
            pressure_list = self._average(array(pressure_list), 2*HIST)
            flow_list = self._average(array(flow_list), 2*HIST)
        if self.plt_history == '1 w':
            ct_list = self._average(array(ct_list), 7*HIST)
            pressure_list = self._average(array(pressure_list), 7*HIST)
            flow_list = self._average(array(flow_list), 7*HIST)
        if self.plt_history == '1 m':
            ct_list = self._average(array(ct_list), 30*HIST)
            pressure_list = self._average(array(pressure_list), 30*HIST)
            flow_list = self._average(array(flow_list), 30*HIST)
        if self.plt_history == '1 y':
            ct_list = self._average(array(ct_list), 365*HIST)
            pressure_list = self._average(array(pressure_list), 365*HIST)
            flow_list = self._average(array(flow_list), 365*HIST)
        # count_list = range(len(pressure_list))
        # count_list_2 = range(len(flow_list))
        # print ('after: ', len(pressure_list))
        try:
            self.curve1.setData(x = ct_list, y = pressure_list, pen = 'r', shadowPen = 'r', symbol='o', symbolSize=1.5, symbolBrush='r', connect='finite')
            self.curve2.setData(x = ct_list, y = flow_list, pen = 'b', shadowPen = 'b', symbol='x', symbolSize=1.5, symbolBrush='b', connect='finite')
        except:
            self.curve1.setData(x = ct_list, y = 0.00, pen = 'r', symbol='o', symbolSize=1.5, symbolBrush='r', connect='finite')
            self.curve2.setData(x = ct_list, y = 0.00, pen = 'b', symbol='x', symbolSize=1.5, symbolBrush='b', connect='finite')

    def closeEvent(self, event):
        """
        Handle 'X' event to minimize to system icon tray instead of closing
        Override the close event to minimize to system tray
        """
        #logger.info("In function: " + inspect.stack()[0][3])
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
        #logger.info("In function: " + inspect.stack()[0][3])
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
        myserver = str(getenv('BPC_SERVER'))
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