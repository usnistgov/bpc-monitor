# Note: For the CCC dewars: 1 inch of lHe is 1 Ltr of lHe
# -*- coding: utf-8 -*-
import sys
from os import environ, chdir, sep, path, mkdir, getcwd, scandir
from argparse import ArgumentParser, ArgumentTypeError

try:
    environ["QT_API"] = "pyqt6"
    from PyQt6 import QtCore, QtGui
    from PyQt6.QtCore import pyqtSignal, QTimer, QThread, QSettings, QObject, QRect
    from PyQt6.QtGui import QAction, QFont, QDoubleValidator, QIcon
    from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,\
                                QLabel, QPushButton, QComboBox,QMessageBox, \
                                QSystemTrayIcon, QStyle, QTabWidget, \
                                QLineEdit, QFrame, QSizePolicy, QMenuBar, QMenu, QTextEdit)
    pixmapi = QStyle.StandardPixmap.SP_TitleBarMenuButton
except ImportError:
    environ["QT_API"] = "pyqt5"
    from PyQt5 import QtCore, QtGui
    from PyQt5.QtGui import QFont, QDoubleValidator, QIcon
    from PyQt5.QtCore import pyqtSignal, QTimer, QThread, QSettings, QObject, QRect
    from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,\
                                QLabel, QPushButton, QComboBox, QMessageBox, \
                                QSystemTrayIcon, QStyle, QAction, QTabWidget,
                                QLineEdit, QFrame, QSizePolicy, QMenuBar, QMenu, QTextEdit)
    pixmapi = QStyle.SP_TitleBarMenuButton

import pyqtgraph as pg
from collections import deque
from datetime import datetime, timedelta
from time import strftime, time, perf_counter, sleep
import inspect, signal
# controller class
import Vision130
from numpy import NaN, mean, array, Inf, isnan
# matplotlib imports
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib
from matplotlib.dates import ConciseDateFormatter, AutoDateLocator
import matplotlib.style as mplstyle
import matplotlib.pyplot as plt
from concurrent.futures import ThreadPoolExecutor

from pandas import read_csv, concat, to_datetime

from pcaspy import SimpleServer, Driver
from pcaspy.tools import ServerThread
# for logging
import logging
from logging.handlers import TimedRotatingFileHandler

from smtplib import SMTP
from email.mime.text import MIMEText

from random import uniform, random

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
# directory to store program logs
# logdir    = "C:" + sep + "_logcache_"
# if path.isdir(logdir) == False:
#     mkdir(logdir)
# Create the logger
logger = logging.getLogger(__name__)
# set the log level
logger.setLevel(logging.INFO)

# import ctypes
# kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
# process_array = (ctypes.c_uint8 * 1)()
# num_processes = kernel32.GetConsoleProcessList(process_array, 1)
# if num_processes < 3: ctypes.WinDLL('user32').ShowWindow(kernel32.GetConsoleWindow(), 0)
# python globals
__version__ = '2.1' # Program version string
MAIN_THREAD_POLL = 1000 # in ms (1 s)
# EMAIL_POLL = 300000 # for testing
EMAIL_POLL = 1.44e7 # in ms (4 hours)
He_EXP_RATIO = 1./754.2 # liquid to gas expansion ratio for Helium at 1 atm and 70 F
WIDTH = 455
HEIGHT= 430
HIST = 24
WORKERS = 8
START_LHE = ''
THRESHOLD_LHE = ''
START_LHE_CHANGED = 0

chdir(base_dir)
# load the main ui file
# main_file = uic.loadUiType(path.join(base_dir, 'ui\\main.ui'))[0]
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
           'figure.dpi': 120,
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
           'savefig.facecolor': '#f0f0f0',
           'figure.raise_window' : True
          }

plt.rc('font', family = 'serif')
matplotlib.rcParams.update(params)

style = """QTabWidget::tab-bar{
           alignment: right;
           }"""

pvdb = {
        'PRESSURE':         {'prec'  : 3,
                             'unit'  : 'mbar',
                             'scan'  : 1},
        'LHE_RECOVERED':    {'prec'  : 6,
                             'unit'  : 'l/day',
                             'scan'  : 1},
        'VALVE':            {'prec'  : 0,
                             'unit'  : '%',
                             'scan'  : 1},
        'HE_FLOW':          {'prec'  : 6,
                             'unit'  : 'l/min',
                             'scan'  : 1},
        'LHE_LEFT':         {'prec'  : 3,
                             'unit'  : 'l',
                             'scan'  : 1},
        'LHE_FIN':          {'prec'  : 2,
                             'unit'  : 'day',
                             'scan'  : 1},
        }

class myDriver(Driver):

    def __init__(self):
       super(myDriver,self).__init__()

class MplCanvas(FigureCanvasQTAgg):

    def __init__(self, parent=None, width=5, height=2, dpi=180):
        self.fig = Figure(figsize=(width, height), dpi=dpi, facecolor='#f0f0f0')
        super(MplCanvas, self).__init__(self.fig)
        self.ax1 = self.fig.add_subplot(111)
        self.ax_settings()

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
    lHe_est_time_to_threshold = pyqtSignal(float)
    remaining_lHe_signal = pyqtSignal(float)
    rec_signal = pyqtSignal(float)

    def __init__(self):
        """
        Constructor for the main thread
        """
        #logger.info("In function: " + inspect.stack()[0][3])
        QtCore.QThread.__init__(self)
        QtCore.QObject.__init__(self)
        self.setTerminationEnabled(True)
        self.integrated_lHe_used = 0.0
        self.remaining_lHe = NaN
        self.calc_time_to_threshold = Inf
        self._kill = False
        self.loop_time = 0
        self.rec = []

    def __del__(self):
        """
        Destructor for the main thread, handles thread termination
        """
        self.wait()
        #logger.info("In function: " + inspect.stack()[0][3])

    def _getRbvs(self,):
        #logger.info("In function: " + inspect.stack()[0][3])
        if debug_mode:
            debug_bpc_rbv = [random() for i in range(24)]
            debug_bpc_rbv[20] = uniform(24.5, 25.5)
            debug_bpc_rbv[-1] = uniform(0,100)
            debug_bpc_rbv[10] = uniform (0, 5)
            return debug_bpc_rbv
        else:
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
        global MAIN_THREAD_POLL
        global START_LHE
        global THRESHOLD_LHE
        global START_LHE_CHANGED
        while 1 and not self._kill:
            try:
                #logger.info("In function: " + inspect.stack()[0][3])
                start_time = perf_counter()
                all_rbv = self._getRbvs()
                if not (isnan(all_rbv[10])):
                    recovered = (correction*all_rbv[10])*60*24/(1./He_EXP_RATIO)
                    self.rec.append(recovered)
                else:
                    recovered = NaN
                # all_rbv.insert(len(all_rbv), recovered)
                # if user enters lHe start ltrs...
                if START_LHE != '':
                    # get the starting lHe from user
                    start_lHe = float(START_LHE)
                    if start_lHe > 0:
                        if not (isnan(recovered)):
                            try:
                                if START_LHE_CHANGED:
                                    self.integrated_lHe_used = 0
                                    START_LHE_CHANGED = 0
                                # instantaneous lHe being used in litres/sec
                                inst_lHe_used = (recovered/86400.0)*self.loop_time
                                # integrated lHe being used in liters
                                if not isnan(inst_lHe_used):
                                    self.integrated_lHe_used = self.integrated_lHe_used + inst_lHe_used
                                # remaining lHe in dewar in percent
                                # remaining_lHe_perc = 100.0 - (self.integrated_lHe_used/start_lHe)*100.0
                                # remaining_lHe used in litres
                                    self.remaining_lHe = round((start_lHe - self.integrated_lHe_used), 4)
                                # print ("Integrated: ", self.integrated_lHe_used, "Remaining %:", remaining_lHe_perc)
                                if float(self.remaining_lHe) <= 0:
                                    self.remaining_lHe = 0
                            except Exception as e:
                                logger.info("In function: " +  inspect.stack()[0][3] + " Exception: " + str(e))
                                pass
                            if THRESHOLD_LHE != '' and float(THRESHOLD_LHE) < start_lHe and mean(self.rec) != 0:
                                start_lHe_threshold_corr = start_lHe - float(THRESHOLD_LHE)
                                self.calc_time_to_threshold = round(((start_lHe_threshold_corr - self.integrated_lHe_used)/mean(self.rec)), 2)

                                #     main_window.lbl_lHe_per_remain_rbv.setStyleSheet("color: red; background-color: black;")
                                # else:
                                #     main_window.lbl_lHe_per_remain_rbv.setStyleSheet("color: rgb(0, 170, 0); background-color: black;")
                            else:
                                self.calc_time_to_threshold = Inf
                    else:
                        # start lHe <=0
                        self.remaining_lHe = NaN
                        self.calc_time_to_threshold = Inf
                        self.integrated_lHe_used = 0
                else:
                    # if start ltr text == ''
                    self.remaining_lHe = NaN
                    self.calc_time_to_threshold = Inf
                    self.integrated_lHe_used = 0

                self.update_data.emit(all_rbv)
                self.lHe_est_time_to_threshold.emit(self.calc_time_to_threshold)
                self.rec_signal.emit(recovered)
                self.remaining_lHe_signal.emit(self.remaining_lHe)
                self.plot_temp.emit()
                #print ("Time taken to execute: ", perf_counter() - start_time )
                if len(self.rec) > 60:
                    self.rec.pop(0)
            except Exception as e:
                self.update_data.emit(all_rbv)
                self.lHe_est_time_to_threshold.emit(self.calc_time_to_threshold)
                self.rec_signal.emit(recovered)
                self.remaining_lHe_signal.emit(NaN)
                # emit this signal last
                self.plot_temp.emit()
                logger.info("In function: " +  inspect.stack()[0][3] + " Exception: " + str(e))
                pass
            sleep(MAIN_THREAD_POLL*0.001)
            # # makes sure that the GUI thread gets processed
            # app.processEvents()
            self.loop_time = perf_counter() - start_time

    def stop(self):
        """
        Stops the main thread gracefully
        """
        self._kill = True
        self.quit()
        self.wait()

class aboutWindow(QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("About")
        self.setFixedSize(300, 200)
        self.te_about = QTextEdit()
        self.te_about.setReadOnly(True)
        self.te_about.setPlainText("Developer & Maintainer: Alireza Panna")
        self.te_about.append("Co-Maintainer: Frank Seifert")
        self.te_about.append("Email: alireza.panna@nist.gov & frank.seifert@nist.gov")
        self.te_about.append("EPICS PV for this server: " + str(PV))
        self.te_about.append("EPICS records: " + str(list(pvdb.keys())))
        self.te_about.append("Current data folder: " + str(datadir))
        self.te_about.append("Current log folder: " + str(logdir))

        layout = QVBoxLayout()
        layout.addWidget(self.te_about)
        self.setLayout(layout)

class mainWindow(QTabWidget):

    def __init__(self):
        global HIST
        global MAIN_THREAD_POLL
        QTabWidget.__init__(self)
        # self.setWindowIcon(QIcon(".\\icons\\main.ico"))
        self.tab1 = QWidget()
        self.addTab(self.tab1, "Viewer")
        self.tab2 = QWidget()
        self.addTab(self.tab2,"History")
        # self.tab3 = QWidget()
        # self.addTab(self.tab3, "lHe Dewar stats")
        self.setStyleSheet(style)
        self.font = QFont()
        self.font.setPointSize(10)
        self.sc = MplCanvas(self, width=5, height=2, dpi=180)
        self.timer = QTimer()
        # self.timer.setTimerType(QtCore.Qt.PreciseTimer)
        self.timer.timeout.connect(self.calc_uptime)
        self.email_timer = QTimer()
        self.email_timer.timeout.connect(self.send_email)
        self.restore_start_lHe = ''
        self.fname = datadir + '\\bpc_log_' + strftime("%Y%m%d") + '.txt'
        self.save_restore_fname = datadir + '\\bpc_save_restore' + '.sav'
        try:
            with open(self.save_restore_fname, 'r') as f:
                restore_start_lHe = (f.read()).split(' ')[-1]
                if (isDigit(restore_start_lHe)):
                    self.restore_start_lHe = restore_start_lHe
        except Exception as e:
            self.restore_start_lHe = ''
            logger.info("In function: " +  inspect.stack()[0][3] + " Exception: " + str(e))
            pass
        self.tab1_ui()
        self.tab2_ui()
        # self.tab3_ui()
        self.setFixedSize(WIDTH, HEIGHT)
        self.tray_icon = None
        # program flags
        self.quit_flag = 0
        self.draw_bpc_flag = 0
        self.timestamp = datetime.now()
        self.settings = QSettings("global_settings.ini", QSettings.Format.IniFormat)
        # self.setupUi(self)
        self.plot_settings()
        self.data_pressure = deque(maxlen=int(86400/(HIST*MAIN_THREAD_POLL*1e-3)))
        self.data_flow = deque(maxlen=int(86400/(HIST*MAIN_THREAD_POLL*1e-3)))
        # start the main thread
        self.mthread = mainThread()
        self.mthread.start()
        self.mthread.update_data.connect(self._getAllData)
        self.mthread.plot_temp.connect(self.plot_data)
        self.mthread.lHe_est_time_to_threshold.connect(self.set_est_lHe)
        self.mthread.rec_signal.connect(self.set_recovered)
        self.mthread.remaining_lHe_signal.connect(self.set_remaining_lHe)

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

        self.close_action = QAction("&Quit", self)
        self.close_action.setStatusTip("Quit this program")
        self.close_action.setShortcut("Ctrl + Q")
        self.close_action.triggered.connect(self.quit)

        self.about_action = QAction("&About", self)
        self.about_action.setStatusTip("Program information & license")
        self.about_action.triggered.connect(self._about)

        self.cb_plt_hist.addItems(['1 min', '5 min', '1 hr', '2 hr', '12 hr', \
                                   '1 d', '2 d', '1 w', '1 m', '1 y'])
        self.cb_plt_hist.setCurrentText('1 hr')
        self.cb_plt_hist.activated.connect(self.set_plot_history)
        self.plt_history = self.cb_plt_hist.currentText()

        self._create_menubar()

        if PV != '':
            self.drv = myDriver()
        #logger.info ("In function: " + inspect.stack()[0][3])
        self.start_time = time()

    def _create_menubar(self, ):
        self.menuBar = QMenuBar(self)
        self.file_menu = self.menuBar.addMenu("&File")
        self.file_menu.addAction(self.close_action)
        self.help_menu = self.menuBar.addMenu("&Help")
        self.help_menu.addAction(self.about_action)

    def _about(self,):
        self.about_window = aboutWindow()
        self.about_window.show()

    def tab1_ui(self, ):
        """
        converted using pyuic
        """
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)

        self.lbl_uptime = QLabel(parent=self.tab1)
        self.lbl_uptime.setGeometry(QRect(30, 347, 41, 20))
        self.lbl_uptime.setFont(self.font)
        self.lbl_uptime.setObjectName("lbl_uptime")

        self.lbl_plt_hist = QLabel(parent=self.tab1)
        self.lbl_plt_hist.setGeometry(QRect(15, 307, 71, 20))
        self.lbl_plt_hist.setFont(self.font)
        self.lbl_plt_hist.setObjectName("lbl_plt_hist")

        self.pw_2 = pg.PlotWidget(parent=self.tab1)
        self.pw_2.setGeometry(QRect(180, 220, 266, 179))
        sizePolicy.setHeightForWidth(self.pw_2.sizePolicy().hasHeightForWidth())
        self.pw_2.setSizePolicy(sizePolicy)
        self.pw_2.setMaximumSize(QtCore.QSize(605, 16777215))
        self.pw_2.setFont(self.font)
        self.pw_2.setLayoutDirection(QtCore.Qt.LayoutDirection.LeftToRight)
        self.pw_2.setStyleSheet("background-color: rgb(240, 240, 240);")
        self.pw_2.setFrameShape(QFrame.Shape.NoFrame)
        self.pw_2.setFrameShadow(QFrame.Shadow.Plain)
        self.pw_2.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.pw_2.setObjectName("pw_2")

        self.cb_plt_hist = QComboBox(parent=self.tab1)
        self.cb_plt_hist.setGeometry(QtCore.QRect(15, 327, 71, 22))
        self.cb_plt_hist.setFont(self.font)
        self.cb_plt_hist.setObjectName("cb_plt_hist")

        self.btn_clr_plots = QPushButton(parent=self.tab1)
        self.btn_clr_plots.setGeometry(QtCore.QRect(100, 322, 75, 31))
        self.btn_clr_plots.setFont(self.font)
        self.btn_clr_plots.setStyleSheet("background-color: rgb(0, 170, 0);\n"
                                         "color: rgb(255, 255, 255);")
        self.btn_clr_plots.setObjectName("btn_clr_plots")

        self.le_uptime = QLineEdit(parent=self.tab1)
        self.le_uptime.setGeometry(QtCore.QRect(7, 370, 91, 31))
        self.le_uptime.setFont(self.font)
        self.le_uptime.setLayoutDirection(QtCore.Qt.LayoutDirection.RightToLeft)
        self.le_uptime.setStyleSheet("background-color: rgb(0, 0, 0);\n"
                                     "color: rgb(0, 170, 0);")
        self.le_uptime.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.le_uptime.setObjectName("le_uptime")

        self.label = QLabel(parent=self.tab1)
        self.label.setGeometry(QtCore.QRect(10, 3, 437, 29))
        font = QtGui.QFont()
        font.setFamily("MS Shell Dlg 2")
        font.setPointSize(13)
        font.setBold(False)
        self.label.setFont(font)
        self.label.setStyleSheet("background-color: rgb(150, 150, 150);\n"
                                 "color: rgb(255, 255, 255);")
        self.label.setFrameShape(QFrame.Shape.Panel)
        self.label.setFrameShadow(QFrame.Shadow.Raised)
        self.label.setLineWidth(3)
        self.label.setMidLineWidth(3)
        self.label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.label.setIndent(0)
        self.label.setObjectName("label")

        self.btn_quit = QPushButton(parent=self.tab1)
        self.btn_quit.setGeometry(QtCore.QRect(100, 370, 75, 31))
        self.btn_quit.setFont(self.font)
        self.btn_quit.setStyleSheet("background-color: rgb(255, 0, 0);\n"
                                    "color: rgb(255, 255, 255);")
        self.btn_quit.setObjectName("btn_quit")

        self.main_frame = QFrame(parent=self.tab1)
        self.main_frame.setEnabled(True)
        self.main_frame.setGeometry(QtCore.QRect(5, 30, 171, 170))
        sizePolicy.setHeightForWidth(self.main_frame.sizePolicy().hasHeightForWidth())
        self.main_frame.setSizePolicy(sizePolicy)
        self.main_frame.setMinimumSize(QtCore.QSize(150, 170))
        self.main_frame.setMaximumSize(QtCore.QSize(181, 170))
        self.main_frame.setAutoFillBackground(True)
        self.main_frame.setStyleSheet("background-color: rgb(140, 140, 140, 150);")
        self.main_frame.setFrameShape(QFrame.Shape.Box)
        self.main_frame.setFrameShadow(QFrame.Shadow.Raised)
        self.main_frame.setLineWidth(3)
        self.main_frame.setObjectName("main_frame")

        self.lbl_flow_rbv = QLabel(parent=self.main_frame)
        self.lbl_flow_rbv.setGeometry(QtCore.QRect(90, 45, 71, 21))
        sizePolicy.setHeightForWidth(self.lbl_flow_rbv.sizePolicy().hasHeightForWidth())
        self.lbl_flow_rbv.setSizePolicy(sizePolicy)
        self.lbl_flow_rbv.setFont(self.font)
        self.lbl_flow_rbv.setStyleSheet("background-color: rgb(0, 0, 0);\n"
                                        "color: rgb(0, 170, 0);")
        self.lbl_flow_rbv.setFrameShadow(QFrame.Shadow.Sunken)
        self.lbl_flow_rbv.setTextFormat(QtCore.Qt.TextFormat.AutoText)
        self.lbl_flow_rbv.setScaledContents(True)
        self.lbl_flow_rbv.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.lbl_flow_rbv.setIndent(0)
        self.lbl_flow_rbv.setObjectName("lbl_flow_rbv")

        self.lbl_pressure_rbv = QLabel(parent=self.main_frame)
        self.lbl_pressure_rbv.setGeometry(QtCore.QRect(90, 15, 71, 21))
        sizePolicy.setHeightForWidth(self.lbl_pressure_rbv.sizePolicy().hasHeightForWidth())
        self.lbl_pressure_rbv.setSizePolicy(sizePolicy)
        self.lbl_pressure_rbv.setFont(self.font)
        self.lbl_pressure_rbv.setStyleSheet("background-color: rgb(0, 0, 0);\n"
                                            "color: rgb(0, 170, 0);")
        self.lbl_pressure_rbv.setFrameShadow(QFrame.Shadow.Sunken)
        self.lbl_pressure_rbv.setTextFormat(QtCore.Qt.TextFormat.AutoText)
        self.lbl_pressure_rbv.setScaledContents(True)
        self.lbl_pressure_rbv.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.lbl_pressure_rbv.setIndent(0)
        self.lbl_pressure_rbv.setObjectName("lbl_pressure_rbv")

        self.lbl_pressure = QLabel(parent=self.main_frame)
        self.lbl_pressure.setGeometry(QtCore.QRect(10, 10, 81, 31))
        self.lbl_pressure.setFont(self.font)
        self.lbl_pressure.setStyleSheet("background-color: rgb(255, 255, 255,0);\n"
                                        "color: rgb(255, 0, 0);")
        self.lbl_pressure.setObjectName("lbl_pressure")

        self.lbl_flow = QLabel(parent=self.main_frame)
        self.lbl_flow.setGeometry(QtCore.QRect(10, 40, 121, 31))
        self.lbl_flow.setFont(self.font)
        self.lbl_flow.setStyleSheet("background-color: rgb(255, 255, 255,0);\n"
                                    "color: rgb(0, 0, 0);")
        self.lbl_flow.setObjectName("lbl_flow")

        self.lbl_valve_rbv = QLabel(parent=self.main_frame)
        self.lbl_valve_rbv.setGeometry(QtCore.QRect(90, 75, 71, 21))
        sizePolicy.setHeightForWidth(self.lbl_valve_rbv.sizePolicy().hasHeightForWidth())
        self.lbl_valve_rbv.setSizePolicy(sizePolicy)
        self.lbl_valve_rbv.setFont(self.font)
        self.lbl_valve_rbv.setStyleSheet("background-color: rgb(0, 0, 0);\n"
                                         "color: rgb(0, 170, 0);")
        self.lbl_valve_rbv.setFrameShadow(QFrame.Shadow.Sunken)
        self.lbl_valve_rbv.setTextFormat(QtCore.Qt.TextFormat.AutoText)
        self.lbl_valve_rbv.setScaledContents(True)
        self.lbl_valve_rbv.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.lbl_valve_rbv.setIndent(0)
        self.lbl_valve_rbv.setObjectName("lbl_valve_rbv")

        self.lbl_valve = QLabel(parent=self.main_frame)
        self.lbl_valve.setGeometry(QtCore.QRect(10, 70, 81, 31))
        self.lbl_valve.setFont(self.font)
        self.lbl_valve.setStyleSheet("background-color: rgb(255, 255, 255,0);\n"
                                     "color: rgb(0, 0, 0);")
        self.lbl_valve.setObjectName("lbl_valve")

        self.lbl_rec_rbv = QLabel(parent=self.main_frame)
        self.lbl_rec_rbv.setGeometry(QtCore.QRect(90, 105, 71, 21))
        sizePolicy.setHeightForWidth(self.lbl_rec_rbv.sizePolicy().hasHeightForWidth())
        self.lbl_rec_rbv.setSizePolicy(sizePolicy)
        self.lbl_rec_rbv.setFont(self.font)
        self.lbl_rec_rbv.setStyleSheet("background-color: rgb(0, 0, 0);\n"
                                       "color: rgb(0, 170, 0);")
        self.lbl_rec_rbv.setFrameShadow(QFrame.Shadow.Sunken)
        self.lbl_rec_rbv.setTextFormat(QtCore.Qt.TextFormat.AutoText)
        self.lbl_rec_rbv.setScaledContents(True)
        self.lbl_rec_rbv.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.lbl_rec_rbv.setIndent(0)
        self.lbl_rec_rbv.setObjectName("lbl_rec_rbv")

        self.lbl_rec = QLabel(parent=self.main_frame)
        self.lbl_rec.setGeometry(QtCore.QRect(10, 100, 121, 31))
        self.lbl_rec.setMinimumSize(QtCore.QSize(0, 31))
        self.lbl_rec.setFont(self.font)
        self.lbl_rec.setStyleSheet("background-color: rgb(255, 255, 255,0);\n"
                                   "color: rgb(238, 130, 238);")
        self.lbl_rec.setObjectName("lbl_rec")

        self.lbl_lHe_per_remain = QLabel(parent=self.main_frame)
        self.lbl_lHe_per_remain.setGeometry(QtCore.QRect(10, 130, 121, 31))
        self.lbl_lHe_per_remain.setMinimumSize(QtCore.QSize(0, 31))
        self.lbl_lHe_per_remain.setFont(self.font)
        self.lbl_lHe_per_remain.setStyleSheet("background-color: rgb(255, 255, 255,0);\n"
                                              "color: rgb(0, 0, 0);")
        self.lbl_lHe_per_remain.setObjectName("lbl_lHe_per_remain")

        self.lbl_lHe_per_remain_rbv = QLabel(parent=self.main_frame)
        self.lbl_lHe_per_remain_rbv.setGeometry(QtCore.QRect(90, 135, 71, 21))
        sizePolicy.setHeightForWidth(self.lbl_lHe_per_remain_rbv.sizePolicy().hasHeightForWidth())
        self.lbl_lHe_per_remain_rbv.setSizePolicy(sizePolicy)
        self.lbl_lHe_per_remain_rbv.setFont(self.font)
        self.lbl_lHe_per_remain_rbv.setStyleSheet("background-color: rgb(0, 0, 0);\n"
                                                  "color: rgb(0, 170, 0);")
        self.lbl_lHe_per_remain_rbv.setFrameShadow(QFrame.Shadow.Sunken)
        self.lbl_lHe_per_remain_rbv.setTextFormat(QtCore.Qt.TextFormat.AutoText)
        self.lbl_lHe_per_remain_rbv.setScaledContents(True)
        self.lbl_lHe_per_remain_rbv.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.lbl_lHe_per_remain_rbv.setIndent(0)
        self.lbl_lHe_per_remain_rbv.setObjectName("lbl_lHe_per_remain_rbv")

        self.pw = pg.PlotWidget(parent=self.tab1)
        self.pw.setGeometry(QtCore.QRect(180, 38, 266, 179))
        sizePolicy.setHeightForWidth(self.pw.sizePolicy().hasHeightForWidth())
        self.pw.setSizePolicy(sizePolicy)
        self.pw.setMaximumSize(QtCore.QSize(605, 16777215))
        self.pw.setFont(self.font)
        self.pw.setLayoutDirection(QtCore.Qt.LayoutDirection.LeftToRight)
        self.pw.setStyleSheet("background-color: rgb(240, 240, 240);")
        self.pw.setFrameShape(QFrame.Shape.NoFrame)
        self.pw.setFrameShadow(QFrame.Shadow.Plain)
        self.pw.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.pw.setObjectName("pw")

        self.lbl_start_ltr = QLabel(parent=self.tab1)
        self.lbl_start_ltr.setGeometry(QtCore.QRect(10, 200, 81, 31))
        self.lbl_start_ltr.setMinimumSize(QtCore.QSize(0, 31))
        self.lbl_start_ltr.setFont(self.font)
        self.lbl_start_ltr.setStyleSheet("background-color: rgb(255, 255, 255,0);\n"
                                         "color: rgb(0, 0, 0);")
        self.lbl_start_ltr.setObjectName("lbl_start_ltr")

        self.le_start_ltr = QLineEdit(parent=self.tab1)
        self.le_start_ltr.setValidator(QDoubleValidator(0, 10000, 3))
        self.le_start_ltr.setGeometry(QtCore.QRect(119, 204, 51, 25))
        self.le_start_ltr.returnPressed.connect(self.lHe_start_updated)
        self.le_start_ltr.setText(self.restore_start_lHe)
        self.lHe_start_updated()
        self.le_start_ltr.setObjectName("le_start_ltr")

        self.lbl_lHe_threshold = QLabel(parent=self.tab1)
        self.lbl_lHe_threshold.setGeometry(QtCore.QRect(10, 230, 111, 31))
        self.lbl_lHe_threshold.setMinimumSize(QtCore.QSize(0, 31))
        self.lbl_lHe_threshold.setFont(self.font)
        self.lbl_lHe_threshold.setStyleSheet("background-color: rgb(255, 255, 255,0);\n"
                                             "color: rgb(0, 0, 0);")
        self.lbl_lHe_threshold.setObjectName("lbl_lHe_threshold")

        self.le_lHe_threshold = QLineEdit(parent=self.tab1)
        self.le_lHe_threshold.setValidator(QDoubleValidator(0, 10000, 3))
        self.le_lHe_threshold.setGeometry(QtCore.QRect(119, 234, 51, 25))
        if THRESHOLD_LHE != '':
            self.le_lHe_threshold.setText(THRESHOLD_LHE)
        self.le_lHe_threshold.returnPressed.connect(self.lHe_threshold_updated)
        self.le_lHe_threshold.setObjectName("le_lHe_threshold")

        self.lbl_lHe_threshold_time_est = QLabel(parent=self.tab1)
        self.lbl_lHe_threshold_time_est.setGeometry(QtCore.QRect(30, 260, 131, 31))
        self.lbl_lHe_threshold_time_est.setFont(self.font)
        self.lbl_lHe_threshold_time_est.setStyleSheet("background-color: rgb(255, 255, 255,0);\n"
                                                      "color: rgb(0, 0, 0);")
        self.lbl_lHe_threshold_time_est.setObjectName("lbl_lHe_threshold_time_est")

        self.lbl_lHe_threshold_time_est_rbv = QLabel(parent=self.tab1)
        self.lbl_lHe_threshold_time_est_rbv.setGeometry(QtCore.QRect(30, 290, 130, 21))
        sizePolicy.setHeightForWidth(self.lbl_lHe_threshold_time_est_rbv.sizePolicy().hasHeightForWidth())
        self.lbl_lHe_threshold_time_est_rbv.setSizePolicy(sizePolicy)
        self.lbl_lHe_threshold_time_est_rbv.setFont(self.font)
        self.lbl_lHe_threshold_time_est_rbv.setStyleSheet("background-color: rgb(0, 0, 0);\n"
                                                          "color: rgb(0, 170, 0);")
        self.lbl_lHe_threshold_time_est_rbv.setFrameShadow(QFrame.Shadow.Sunken)
        self.lbl_lHe_threshold_time_est_rbv.setTextFormat(QtCore.Qt.TextFormat.AutoText)
        self.lbl_lHe_threshold_time_est_rbv.setScaledContents(True)
        self.lbl_lHe_threshold_time_est_rbv.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.lbl_lHe_threshold_time_est_rbv.setIndent(0)
        self.lbl_lHe_threshold_time_est_rbv.setObjectName("lbl_lHe_threshold_time_est_rbv")

        _translate = QtCore.QCoreApplication.translate
        self.lbl_uptime.setText(_translate("TabWidget", "uptime "))
        self.lbl_plt_hist.setText(_translate("TabWidget", "Plot history"))
        self.btn_clr_plots.setText(_translate("TabWidget", "CLR PLOTS"))
        self.label.setText(_translate("TabWidget", "BACK PRESSURE CONTROLLER VIEWER"))
        self.btn_quit.setText(_translate("TabWidget", "QUIT"))
        self.lbl_flow_rbv.setText(_translate("TabWidget", ""))
        self.lbl_pressure_rbv.setText(_translate("TabWidget", ""))
        self.lbl_pressure.setText(_translate("TabWidget", "P [mbar]"))
        self.lbl_flow.setText(_translate("TabWidget", "He Flow [l/m]"))
        self.lbl_valve_rbv.setText(_translate("TabWidget", ""))
        self.lbl_valve.setText(_translate("TabWidget", "Valve [%]"))
        self.lbl_rec_rbv.setText(_translate("TabWidget", ""))
        self.lbl_rec.setText(_translate("TabWidget", "lHe Rec [l/d]"))
        self.lbl_lHe_per_remain.setText(_translate("TabWidget", "lHe left [ltr]"))
        self.lbl_lHe_per_remain_rbv.setText(_translate("TabWidget", ""))
        self.lbl_start_ltr.setText(_translate("TabWidget", "lHe Start [ltr]"))
        self.lbl_lHe_threshold.setText(_translate("TabWidget", "lHe threshold [ltr]"))
        self.lbl_lHe_threshold_time_est.setText(_translate("TabWidget", "Est. time to threshold"))
        self.lbl_lHe_threshold_time_est_rbv.setText(_translate("TabWidget", ""))

    def tab2_ui(self, ):
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
        layout.addLayout(layout2)
        layout.addWidget(toolbar)
        layout.addWidget(self.sc)
        self.tab2.setLayout(layout)

    def plot_my_data(self,):
        global WORKERS
        #logger.info("In function: " + inspect.stack()[0][3])
        self.btn_plot.setEnabled(False)
        try:
            with ThreadPoolExecutor(max_workers=WORKERS) as executor:
                self.df_bpcCtrl = (executor.submit(self.get_my_data))
            self.df_bpcCtrl = self.df_bpcCtrl.result()
            self.redraw()
        except Exception as e:
            logger.info("In function: " +  inspect.stack()[0][3] + " Exception: " + str(e))
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
        mydata = []
        data   = []
        get_data_start = perf_counter()
        try:
            #print ("In get_my_data")
            i = 0
            for filename in scandir(datadir + '\\'):
                self.filename = filename.name
                if self.filename != '' and (self.filename.split('.')[-1]).rstrip() == 'txt':
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
        Show the main window and start the timer to perform uptime task
        """
        global MAIN_THREAD_POLL
        #logger.info("In function: " + inspect.stack()[0][3])
        QMainWindow.show(self)
        self.sc.fig.tight_layout()

        # run the main thread every 1s
        self.timer.start(MAIN_THREAD_POLL)
        self.timer_start = perf_counter()

    def _exit_app(self):
        """
        Helper function to exit from system tray
        """
        #logger.info("In function: " + inspect.stack()[0][3])
        self.quit_flag = 1
        self.quit()

    def _getAllData(self, all_rbv):
         # print("% remain:", all_rbv[-1])
         try:
             self.timestamp = datetime.now()
             self.lbl_pressure_rbv.setText(str(round(all_rbv[20], 3)))
             self.lbl_flow_rbv.setText(str(round(all_rbv[10]*correction, 3)))
             self.lbl_valve_rbv.setText(str(round(all_rbv[-1], 3)))
             # rec = all_rbv[10]*60*24/(1./He_EXP_RATIO)
             # write to epics pv records
             if PV != '':
                 self.drv.write('PRESSURE', all_rbv[20])
                 self.drv.write('VALVE', all_rbv[-1] )
                 self.drv.write('HE_FLOW', all_rbv[10]*correction)
                 self.drv.updatePVs()
         except Exception as e:
             logger.info("In function: " +  inspect.stack()[0][3] + " Exception: " + str(e))
             pass

    def lHe_start_updated(self,):
        global START_LHE
        global START_LHE_CHANGED
        START_LHE = self.le_start_ltr.text()
        self.lbl_lHe_per_remain_rbv.setText(self.le_start_ltr.text())
        START_LHE_CHANGED = 1
        # stop the email timer if the lHe start is updated
        if self.email_timer.isActive():
            self.email_timer.stop()

    def lHe_threshold_updated(self,):
        global THRESHOLD_LHE
        THRESHOLD_LHE = self.le_lHe_threshold.text()

    def set_est_lHe(self, calc_time_to_threshold):
        if calc_time_to_threshold == Inf:
            self.lbl_lHe_threshold_time_est_rbv.setText('')
        else:
            self.lbl_lHe_threshold_time_est_rbv.setText(str(round(calc_time_to_threshold, 2)) + ' days')
        if PV != '':
            self.drv.write('LHE_FIN', float(calc_time_to_threshold))
            self.drv.updatePVs()

    def set_recovered(self, recovered):
        self.lbl_rec_rbv.setText(str(round(recovered, 3)))
        if PV != '':
            self.drv.write('LHE_RECOVERED', recovered)
            self.drv.updatePVs()

    def set_remaining_lHe(self, remaining_lHe):
        global EMAIL_POLL
        global THRESHOLD_LHE
        if isnan(remaining_lHe):
            self.lbl_lHe_per_remain_rbv.setText('')
        else:
            self.lbl_lHe_per_remain_rbv.setText(str(round(remaining_lHe, 3)))
        if THRESHOLD_LHE != '' and not isnan(remaining_lHe):
            if remaining_lHe <= float(THRESHOLD_LHE):
                if receiver != ['']:
                    if not self.email_timer.isActive():
                        self.send_email()
                        # self.email_timer.start(3600000) # test
                        self.email_timer.start(int(EMAIL_POLL))
        if PV != '':
            self.drv.write('LHE_LEFT', remaining_lHe)
            self.drv.updatePVs()

    def send_email(self,):
        # print("sending email...")
        resource = "smtp.nist.gov"
        port = 25
        sender = "alireza.panna@nist.gov"
        subject = "LHe at threshold"
        body = """ <html>
                   <head></head>
                   <body>
                   <p>Hello user,<br>
                      The LHe level in your dewar is below the set threshold level.<br>
                      Remaining lHe in your dewar: """ + self.lbl_lHe_per_remain_rbv.text() + """ ltrs
                     <br>Please re-fill or exchange dewar.<br><br>
                      Thank you<br><br>
                      Best,<br>
                      Your friendly service galley lHe monitor
                   </p>
                   </body>
                   </html> """
        msg = MIMEText(body, "html")
        msg["From"] = sender
        msg["Subject"] = subject
        msg["To"] = ", ".join(receiver)
        smtp_server = SMTP(resource, port)
        try:
            smtp_server.sendmail(sender, receiver, msg.as_string())
        finally:
            smtp_server.quit()

    def calc_uptime(self):
        """
        A QTimer is used to calculate uptime every second.
        We also use this to update the filename of the data file
        """
        try:
            up = timedelta(seconds=(time() - self.start_time))
            days = int((up.days))
            hours = int((up.seconds/3600)%24)
            mins = int((up.seconds/60)%60)
            secs = int(up.seconds%60)
            self.le_uptime.setText(str(days) + 'd, ' + str(hours) + \
                                  ':' + str(mins) + ':' + str(secs))
            self.fname = datadir + '\\bpc_log_' + strftime("%Y%m%d") + '.txt'
            # if not self.mthread.isRunning():
            #     self.actual_time_taken = perf_counter() - self.timer_start
            #     self.timer_start = perf_counter()
            #     #logger.info("In function: " + inspect.stack()[0][3])
            #     self.mthread.start()
        except Exception as e:
            logger.info("In function: " +  inspect.stack()[0][3] + " Exception: " + str(e))
            # if self.mthread.isRunning():
            #     self.mthread.stop()
            pass


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
        labelStyle_y2 = {'color': 'violet' , 'font-size': '8pt'}
        labelStyle_x = {'color': 'black', 'font-size': '8pt'}
        self.pw.plotItem.clear()
        self.pw_2.plotItem.clear()
        self.pw.setBackground((0,0,0,240))
        self.pw_2.setBackground((0,0,0,240))
        self.pw.plotItem.setLabel(axis='left', text='P', units= 'mbar', **labelStyle_y1)
        self.pw_2.plotItem.setLabel(axis='left', text='lHe Rec.', units='l/day',  **labelStyle_y2)
        self.pw_2.plotItem.setLabel(axis='bottom', text = 'time', units='HH:MM:SS', **labelStyle_x)
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

        if pressure != 'nan' or flow != 'nan' or valve != 'nan':
            self.data_pressure.append({'x':ct, 'y':float(pressure),})
            self.data_flow.append({'x':ct, 'y':float(rec),})
            with open(self.fname, 'a') as f:
                f.write(str(self.timestamp) + '\t' + str(pressure) + '\t' + str(flow) + '\t' + str(valve) + '\n')
            self.lbl_lHe_per_remain_rbv.text().rstrip('\s')
            self.lbl_lHe_per_remain_rbv.text().lstrip('\s')
            with open(self.save_restore_fname, 'w') as f:
                if str(self.lbl_lHe_per_remain_rbv.text() != '' and isDigit(self.lbl_lHe_per_remain_rbv.text())):
                    f.write(str(datetime.now())[:-3] + ' lHe remaining [ltrs]: ' + str(self.lbl_lHe_per_remain_rbv.text()))
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
            self.curve1.setData(x=ct_list, y=pressure_list, pen = 'r', shadowPen = 'r', symbol='o', symbolSize=1.5, symbolBrush='r', connect='finite')
            self.curve2.setData(x=ct_list, y=flow_list, pen=(138,43,226), shadowPen =(138,43,226), symbol='x', symbolSize=1.5, symbolBrush= (138,43,226), connect='finite')
        except:
            self.curve1.setData(x=ct_list, y=0.00, pen='r', symbol='o', symbolSize=1.5, symbolBrush='r', connect='finite')
            self.curve2.setData(x=ct_list, y=0.00, pen=(138,43,226), symbol='x', symbolSize=1.5, symbolBrush=(138,43,226), connect='finite')

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
                msecs=100
            )
            event.ignore()
        if self.quit_flag == 1:
            self.tray_icon.showMessage(
                "BPC Monitor",
                "Terminating the application",
                QSystemTrayIcon.MessageIcon.Information,
                msecs=100
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
                if not debug_mode:
                    mybpc.close_comm()
                if PV != '':
                    server_thread.stop()
                self.mthread.stop()
                file_handler.close()
                self.close()
                QtCore.QCoreApplication.instance().quit
                app.quit()
            else:
                pass
        if self.quit_flag == 1:
            if not debug_mode:
                mybpc.close_comm()
            if PV != '':
                server_thread.stop()
            self.mthread.stop()
            file_handler.close()
            self.close()
            QtCore.QCoreApplication.instance().quit
            app.quit()
#################################################################################################
def _sigint_handler(*args):
    """
    Handler for the SIGINT signal. For testing purposes only
    """
    sys.stderr.write('\r')
    if PV != '':
        server_thread.stop()
    QtGui.QApplication.quit()
    
def isDigit(x):
    try:
        float(x)
        return True
    except ValueError:
        return False

def dir_path(save_path):
    save_path = str(save_path)
    if not path.isdir(save_path):
        mkdir(save_path)
    return save_path

def range_limited_float_type(arg):
    """ 
    Type function for argparse - a float within some predefined bounds
    """
    MIN_VAL = 1
    MAX_VAL = 2
    try:
        f = float(arg)
    except ValueError:    
        raise ArgumentTypeError("Must be a floating point number")
    if f < MIN_VAL or f > MAX_VAL:
        raise ArgumentTypeError("Argument must be <= " + str(MAX_VAL) + " and >= " + str(MIN_VAL))
    return f

if __name__ == '__main__':
    # user options to run multiple instances with different configurations for example
    parser = ArgumentParser(prog = 'bpc-monitor',
                            description='Configure bpc-monitor.',
                            epilog='A utility to log data and estimate lHe usage from the back pressure controller', add_help=True)
    parser.add_argument('-i', '--host', help='specify the host address', default='172.30.33.212')
    parser.add_argument('-p', '--port',  help='specify the port', default='20256', type=int)
    parser.add_argument('-e', '--epics_pv',  help='Specify the PV epics prefix', default='')
    parser.add_argument('-s', '--save_path', help='Specify data directory', default="C:" + sep + "_datacache_", type=dir_path)
    parser.add_argument('-l', '--log_path', help='Specify log directory', default="C:" + sep + "_logcache_", type=dir_path)
    parser.add_argument('-m', '--mail', help='Specify receipients email address', default='')
    parser.add_argument('-d', '--debug', help='Debugging mode', action='store_true')
    parser.add_argument('-t', '--threshold',  help='Specify lHe threshold in ltrs', default='', type=str)
    parser.add_argument('-c', '--correction',  help='Specify correction factor between 1.0 and 2.0', default='1.0', type=range_limited_float_type)

    args, unk = parser.parse_known_args()
    if unk:
        logger.info("Warning: Ignoring unknown arguments: {:}".format(unk))
        pass
    myserver = args.host
    port = args.port
    PV = args.epics_pv
    datadir = args.save_path
    logdir = args.log_path
    receiver = args.mail.split(';')
    debug_mode = args.debug
    threshold = args.threshold
    correction = args.correction
    
    if correction == '':
        correction = 1.0
    if threshold != '':
        THRESHOLD_LHE = threshold
    else:
        THRESHOLD_LHE = ''
    print('Server: ', myserver, 
          'Port: ', port,
          'PV: ', PV, 
          'Datadir: ', datadir,
          'Logdir: ', logdir,
          'Receiver: ', receiver,
          'Debug mode: ', debug_mode,
          'Threshold: ', THRESHOLD_LHE,
          'Correction: ', correction)
    # define the file handler and formatting
    lfname = logdir + sep + 'bpc-monitor' + '.log'
    file_handler = TimedRotatingFileHandler(lfname, when='midnight')
    fmt = logging.Formatter('%(asctime)s : %(levelname)s : %(name)s : %(message)s')
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)
    logger.info('Starting the bpc-monitor with the following settings: ' + \
                'Server: ' + str(myserver) + \
                ', Port: ' +  str(port) + \
                ', PV: ' +  str(PV) + \
                ', Datadir: ' + str(datadir) + \
                ', Logdir: ' + str(logdir) + \
                ', Receiver: ' + str(receiver) + \
                ', Debug mode: ' + str(debug_mode) + \
                ', Threshold: ' + str(THRESHOLD_LHE) + \
                ', Correction Factor: ' + str(correction))
    # logger.info("In function: " +  inspect.stack()[0][3] + "EPICS PV for this server: " + str(PV))
    # Handle high resolution displays:
    if hasattr(QtCore.Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    if hasattr(QtCore.Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)
    # Create the Qt application
    app = QApplication(sys.argv)
    # create pcas server
    if PV != '':
        if not PV.endswith(':'):
            prefix = PV + ':'
        else:
            prefix = PV
        server = SimpleServer()
        server.createPV(prefix, pvdb)
    if not debug_mode:
        mybpc = Vision130.Vision130Driver(myserver, port)
    # Create the main window
    main_window = mainWindow()
    # Remove the title bar and set to fixed geometry to match our touch screen display
    # main_window.setWindowFlags(QtCore.Qt.FramelessWindowHint)
    main_window.setGeometry(500, 500, WIDTH, HEIGHT)
    # Set the program version
    if debug_mode:
        main_window.setWindowTitle("BPC Monitor " + __version__ + ' Debug mode')
    else:
        main_window.setWindowTitle("BPC Monitor " + __version__)
    main_window.show()
    # handle ctrl+c event
    signal.signal(signal.SIGINT, _sigint_handler)
    # create pcas server thread and shut down when app exits
    if PV != '':
        server_thread = ServerThread(server)
        # start pcas event loop
        server_thread.start()
    # Start the GUI thread
    sys.exit(app.exec())