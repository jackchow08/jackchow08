# -*- coding: utf-8 -*-
"""
Merged TDC1 Control + Virtual Lab + Malus Law + Real Exp Analysis
Theme: High Contrast Black & White (Scientific Style)
Updates: Pairs Plotting Fixed, TTL Default, g2 Range 0-100ns
"""

import sys
import math
import random
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import (QMainWindow, QAction, qApp, QApplication, QMenu,
    QWidget, QGridLayout, QVBoxLayout, QHBoxLayout, QDialog, QRadioButton, QSpinBox,
    QDoubleSpinBox, QTabWidget, QComboBox, QMessageBox, QGroupBox, QCheckBox,
    QSlider, QLabel, QPushButton, QFrame, QLineEdit, QTableWidget, QTableWidgetItem, 
    QHeaderView, QScrollArea, QSplitter, QSizePolicy)
from PyQt5.QtGui import QIcon, QFont, QColor, QPainter, QPen, QPainterPath, QPalette
from PyQt5.QtCore import QSize, QTimer, bin_, Qt
import pyqtgraph as pg

import numpy as np
from datetime import datetime
import time

# Try importing S15lib
try:
    from S15lib.instruments import usb_counter_fpga as tdc1
    from S15lib.instruments import serial_connection
    S15LIB_AVAILABLE = True
except ImportError:
    S15LIB_AVAILABLE = False
    print("Warning: S15lib not found. Hardware features will be disabled, but Virtual Lab will work.")

PLT_SAMPLES = 501 # plot samples

# --- STYLESHEET (High Contrast Black & White) ---
BLACK_STYLESHEET = """
QMainWindow, QWidget, QScrollArea {
    background-color: #000000;
    color: #ffffff;
    font-family: "Segoe UI", "Helvetica", sans-serif;
    font-size: 14px;
}
QLabel {
    color: #ffffff;
}
QGroupBox {
    border: 1px solid #ffffff;
    border-radius: 4px;
    margin-top: 24px;
    padding-top: 14px;
    font-weight: bold;
    color: #3daee9; 
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
    background-color: #000000;
}
QPushButton {
    background-color: #333333;
    color: white;
    border: 1px solid #666;
    border-radius: 4px;
    padding: 8px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #555555;
    border: 1px solid #ffffff;
}
QPushButton:disabled {
    background-color: #111;
    color: #555;
    border: 1px solid #333;
}
/* Stop Button Style */
QPushButton#LiveButton[active="true"] {
    background-color: #b00000; 
    border: 1px solid #ff0000;
}
QPushButton#LiveButton[active="true"]:hover {
    background-color: #ff0000;
}
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background-color: #000000;
    border: 1px solid #ffffff;
    border-radius: 4px;
    padding: 6px;
    color: white;
    font-size: 14px;
    selection-background-color: #3daee9;
}
QComboBox::drop-down {
    border: 0px;
    background-color: #333;
    width: 20px;
}
QComboBox QAbstractItemView {
    background-color: #111;
    color: white;
    border: 1px solid white;
}
QTabWidget::pane {
    border: 1px solid #ffffff;
    background-color: #000000;
}
QTabBar::tab {
    background-color: #111;
    color: #aaa;
    border: 1px solid #444;
    padding: 10px 24px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}
QTabBar::tab:selected {
    background-color: #000000;
    color: #ffffff;
    font-weight: bold;
    border: 1px solid #ffffff;
    border-bottom: 2px solid #000000;
}
QTableWidget {
    gridline-color: #ffffff;
    background-color: #000000;
    color: white;
    border: 1px solid #ffffff;
}
QHeaderView::section {
    background-color: #222;
    color: white;
    border: 1px solid #ffffff;
    padding: 6px;
    font-weight: bold;
}
QTableCornerButton::section {
    background-color: #222;
    border: 1px solid #ffffff;
}
QScrollBar:vertical {
    background: #111;
    width: 14px;
}
QScrollBar::handle:vertical {
    background: #555;
    border-radius: 7px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    background: none;
}
"""

# --- CLASS TO DISABLE SCROLLING ON SPINBOXES ---
class NoScrollSpinBox(QtWidgets.QSpinBox):
    def __init__(self, *args, **kwargs):
        super(NoScrollSpinBox, self).__init__(*args, **kwargs)
        self.setFocusPolicy(Qt.StrongFocus)

    def wheelEvent(self, event):
        event.ignore()

# --- OPTICAL SCHEMATIC CLASS (Black Background) ---
class OpticalSchematic(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(250)
        self.hwp_angle = 0
        self.alice_angle = 0
        self.bob_angle = 0
        self.col_bg = Qt.black
        self.col_text = Qt.white
        self.col_laser = QColor("#4A90E2") 
        self.col_beam = QColor("#ff3333") 
        self.col_pump = QColor("#d050d0") 
        self.col_optics = QColor("#ffffff") 
        self.col_hwp = QColor("#ffff00") 

    def set_angles(self, hwp, alice, bob):
        self.hwp_angle = hwp
        self.alice_angle = alice
        self.bob_angle = bob
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), self.col_bg)
        
        try:
            w = self.width()
            h = self.height()
            cy = h // 2
            
            # Laser Source
            painter.setBrush(self.col_laser)
            painter.setPen(Qt.NoPen)
            painter.drawRect(10, cy - 15, 40, 30)
            self.drawText(painter, 10, cy + 35, "Pump")

            # Pump Beam
            pen_pump = QPen(self.col_pump, 2, Qt.DashLine)
            painter.setPen(pen_pump)
            painter.drawLine(50, cy, int(w * 0.45), cy) 

            # HWP
            hwp_x = int(w * 0.25)
            self.drawRotatableElement(painter, hwp_x, cy, self.hwp_angle, "HWP", color=self.col_hwp)

            # Crystal
            crys_x = int(w * 0.45)
            painter.resetTransform()
            painter.setBrush(QColor("#444")) 
            painter.setPen(QPen(self.col_text, 2)) 
            path = QPainterPath()
            path.moveTo(crys_x, cy - 20)
            path.lineTo(crys_x + 15, cy)
            path.lineTo(crys_x, cy + 20)
            path.lineTo(crys_x - 15, cy)
            path.closeSubpath()
            painter.drawPath(path)
            self.drawText(painter, crys_x - 15, cy + 40, "BBO")

            # Beams
            painter.setPen(QPen(self.col_beam, 2))
            alice_x, alice_y = w - 80, cy - 60
            painter.drawLine(crys_x + 15, cy, alice_x, alice_y)
            bob_x, bob_y = w - 80, cy + 60
            painter.drawLine(crys_x + 15, cy, bob_x, bob_y)

            # Detectors
            self.drawRotatableElement(painter, alice_x, alice_y, self.alice_angle, "Alice (A)", color=self.col_optics)
            self.drawRotatableElement(painter, bob_x, bob_y, self.bob_angle, "Bob (B)", color=self.col_optics)
            
        finally:
            painter.end()

    def drawRotatableElement(self, painter, x, y, angle, label, color):
        painter.save()
        painter.translate(x, y)
        painter.setPen(self.col_text)
        painter.drawText(-20, 50, label)
        painter.rotate(-angle) 
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(color, 3))
        painter.drawEllipse(-15, -15, 30, 30)
        painter.setPen(QPen(self.col_text, 2))
        painter.drawLine(0, -15, 0, 15) 
        painter.restore()

    def drawText(self, painter, x, y, text):
        painter.setPen(self.col_text)
        painter.drawText(x, y, text)


# --- MALUS SCHEMATIC CLASS (Black Background) ---
class MalusSchematic(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(200) 
        self.angle = 0
        self.col_bg = Qt.black
        self.col_text = Qt.white
        self.col_laser = QColor("#ff3333") 
        self.col_pol = QColor("#3498DB") 

    def set_angle(self, angle):
        self.angle = angle
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), self.col_bg)

        try:
            w = self.width()
            h = self.height()
            cy = h // 2
            laser_x = 30
            pol_x = w // 2
            det_x = w - 60
            
            painter.setBrush(self.col_laser)
            painter.setPen(Qt.NoPen)
            painter.drawRect(laser_x, cy - 15, 40, 30)
            self.drawText(painter, laser_x, cy + 35, "Laser")

            pen_beam = QPen(self.col_laser, 4)
            painter.setPen(pen_beam)
            painter.drawLine(laser_x + 40, cy, pol_x, cy)

            rad = math.radians(self.angle)
            intensity_factor = math.cos(rad) ** 2
            alpha = int(255 * intensity_factor)
            beam_color = QColor(self.col_laser)
            beam_color.setAlpha(alpha)
            pen_beam_var = QPen(beam_color, 4)
            painter.setPen(pen_beam_var)
            painter.drawLine(pol_x, cy, det_x, cy)

            self.drawRotatableElement(painter, pol_x, cy, self.angle, "Polarizer", self.col_pol)

            painter.setBrush(QColor("#333"))
            painter.setPen(QPen(self.col_text, 2))
            path = QPainterPath()
            path.moveTo(det_x, cy - 20)
            path.arcTo(det_x - 10, cy - 20, 20, 40, 90, -180)
            path.closeSubpath()
            painter.drawPath(path)
            self.drawText(painter, det_x - 15, cy + 35, "Detector")
            
        finally:
            painter.end()

    def drawRotatableElement(self, painter, x, y, angle, label, color):
        painter.save()
        painter.translate(x, y)
        painter.setPen(self.col_text)
        painter.drawText(-25, 50, label)
        painter.rotate(-angle) 
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(color, 4))
        painter.drawEllipse(-20, -20, 40, 40)
        painter.setPen(QPen(self.col_text, 2, Qt.DashLine))
        painter.drawLine(0, -20, 0, 20)
        painter.restore()

    def drawText(self, painter, x, y, text):
        painter.setPen(self.col_text)
        painter.drawText(x, y, text)

# --- WORKER CLASS ---
class logWorker(QtCore.QObject):
    data_is_logged = QtCore.pyqtSignal(float, float, tuple, str, list)
    histogram_logged = QtCore.pyqtSignal(dict, int, int)
    coincidences_data_logged = QtCore.pyqtSignal('PyQt_PyObject') 
    thread_finished = QtCore.pyqtSignal('PyQt_PyObject')
    permission_error = QtCore.pyqtSignal('PyQt_PyObject')

    def __init__(self):
        super(logWorker, self).__init__()
        self.active_flag = False
        self.radio_flags = [0,0,0,0] 
        self.int_time = 1
        self.ch_start = 1
        self.ch_stop = 3
        self.bin_width = 2
        self.bins = 501
        self.offset = 0
        self.runtime = 0
    
    @QtCore.pyqtSlot(float, str, str, bool, str, object, int, int, int, int)
    def log_which_data(self, int_time: float, file_name: str, device_path: str, log_flag: bool, \
        dev_mode: str, tdc1_dev: object, start: int, stop: int, offset: int, bin_width: int):
        self.int_time = int_time
        self.ch_start = start
        self.ch_stop = stop
        self.offset = offset
        self.bin_width = bin_width
        self.active_flag = True
        if dev_mode == 'singles':
            print('initiating singles log...')
            self.log_counts_data(file_name, device_path, log_flag, dev_mode, tdc1_dev)
        elif dev_mode == 'g2':
            print('initiating g2 log...')
            self.log_g2(file_name, device_path, log_flag, dev_mode, tdc1_dev)
        elif dev_mode == 'pairs':
            print('initiating pairs log')
            self.log_coincidences_data(file_name, device_path, log_flag, dev_mode, tdc1_dev)

    def log_counts_data(self, file_name: str, device_path: str, log_flag: bool, dev_mode: str, tdc1_dev: object):
        start = time.time()
        now = start
        if log_flag == True and self.active_flag == True:
            try:
                open(file_name)
            except IOError:
                f = open(file_name, 'w')
                f.write('#time_stamp,counts\n')
            while self.active_flag == True:
                counts = tdc1_dev.get_counts(self.int_time)
                now = time.time()
                self.data_is_logged.emit(start, now, counts, dev_mode, self.radio_flags)
                try:
                    with open(file_name, 'a+') as f:
                        time_data: str = datetime.now().isoformat()
                        data_pairs = '{},{},{},{},{}\n'.format(time_data, *counts)
                        f.write(data_pairs)
                    if self.active_flag == False:
                        break
                except PermissionError:
                    tdc1_dev._com.reset_input_buffer()
                    self.permission_error.emit(tdc1_dev)
                    return
        elif log_flag == False:
            while self.active_flag == True:
                counts = tdc1_dev.get_counts(self.int_time)
                now = time.time()
                self.data_is_logged.emit(start, now, counts, dev_mode, self.radio_flags)
                if self.active_flag == False:
                    break
        print('terminating singles log.')
        self.thread_finished.emit(tdc1_dev)

    def log_coincidences_data(self, file_name: str, device_path: str, log_flag: bool, dev_mode: str, tdc1_dev: object):
        start = time.time()
        now = start
        if log_flag == True and self.active_flag == True:
            try:
                open(file_name)
            except IOError:
                f = open(file_name, 'w')
                f.write('#time_stamp,coincidences\n')
            while self.active_flag == True:
                coincidences = tdc1_dev.get_counts_and_coincidences(self.int_time)
                now = time.time()
                self.data_is_logged.emit(start, now, coincidences, dev_mode, self.radio_flags)
                try:
                    with open(file_name, 'a+') as f:
                        time_data: str = datetime.now().isoformat()
                        data_pairs = '{},{},{},{},{},{},{},{},{}\n'.format(time_data, *coincidences)
                        f.write(data_pairs)
                    if self.active_flag == False:
                        break
                except PermissionError:
                    tdc1_dev._com.reset_input_buffer()
                    self.permission_error.emit(tdc1_dev)
                    return
        elif log_flag == False:
            while self.active_flag == True:
                coincidences = tdc1_dev.get_counts_and_coincidences(self.int_time)
                now = time.time()
                self.data_is_logged.emit(start, now, coincidences, dev_mode, self.radio_flags)
                if self.active_flag == False:
                        break
        print('terminating pairs log.')
        self.thread_finished.emit(tdc1_dev)

    def log_g2(self, file_name: str, device_path: str, log_flag: bool, dev_mode: str, tdc1_dev: object):
        start = time.time()
        now = start
        if log_flag == True and self.active_flag == True:
            try:
                open(file_name)
            except IOError:
                f = open(file_name, 'w')
                f.write('#time_stamp,g2\n')
            while self.active_flag == True:
                g2_dict = tdc1_dev.count_g2(t_acq = self.int_time, ch_start = self.ch_start, ch_stop = self.ch_stop, \
                    bin_width = self.bin_width, bins = self.bins, ch_stop_delay = self.offset)
                now = time.time()
                hist = g2_dict['histogram']
                self.histogram_logged.emit(g2_dict, self.bins, self.bin_width)
                try:
                    with open(file_name, 'a+') as f:
                        time_data: str = datetime.now().isoformat()
                        hist_list = hist.tolist()
                        new_hist = [str(element) for element in hist_list]
                        new_hist.insert(0, time_data)
                        data = ','.join(new_hist) + '\n'
                        f.write(data)
                    if self.active_flag == False:
                        break
                except PermissionError:
                    tdc1_dev._com.reset_input_buffer()
                    self.permission_error.emit(tdc1_dev)
                    return
        elif log_flag == False:
            while self.active_flag == True:
                g2_dict = tdc1_dev.count_g2(t_acq = self.int_time, ch_start = self.ch_start, ch_stop = self.ch_stop, \
                    bin_width = self.bin_width, bins = self.bins, ch_stop_delay = self.offset)
                now = time.time()
                self.histogram_logged.emit(g2_dict, self.bins, self.bin_width)
                if self.active_flag == False:
                        break
        print('terminating g2 log.')
        self.thread_finished.emit(tdc1_dev)
        

class MainWindow(QMainWindow):
    logging_requested = QtCore.pyqtSignal(float, str, str, bool, str, object, int, int, int, int)
    
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        self._tdc1_dev = None  
        self._dev_mode = '' 
        self._dev_path = '' 
        self._level = '' 
        self._dev_selected = False
        self.dev_list = []

        self.log_flag = False  
        self.acq_flag = False 
        self._radio_flags = [0,0,0,0] 
        self.logger = None 
        self.logger_thread = None 

        # --- Virtual Lab Internal State ---
        self.virt_current_A = 0
        self.virt_current_B = 0
        self.virt_hwp_angle = 0
        self.virt_laserOn = True
        self.virt_notebook = {
            'e1': {'val': None, 'label': "A=0, B=22.5", 'a': 0, 'b': 22.5},
            'e2': {'val': None, 'label': "A=0, B=67.5", 'a': 0, 'b': 67.5},
            'e3': {'val': None, 'label': "A=45, B=22.5", 'a': 45, 'b': 22.5},
            'e4': {'val': None, 'label': "A=45, B=67.5", 'a': 45, 'b': 67.5},
        }
        
        self.hwp_angle_labels = []
        self.hwp_state_labels = []
        self.malus_laserOn = True
        self.virt_MAX_COUNTS = 250  
        self.virt_DARK_COUNTS = 20
        self.virt_VISIBILITY = 0.98 
        
        self.initUI() 

        self.integration_time = int(self.integrationSpinBox.text())
        self._logfile_name = '' 
        self._ch_start = int(self.channelsCombobox1.currentText()) 
        self._ch_stop = int(self.channelsCombobox2.currentText()) 
        self.plotSamples = self.samplesSpinbox.value() 
        self.offset = self.offsetSpinbox.value()
        self.bin_width = self.resolutionSpinbox.value()
        self._runtime = self.runtimeSpinbox.value() * 60 

        # Variables for GUI 'memory'
        self._dev_path_prev = self.devCombobox.currentText()
        self._dev_mode_prev = self.modesCombobox.currentText()
        self._level_prev = self.levelsComboBox.currentText()
        self.integration_time_prev = self.integration_time
        self.plotSamples_prev = self.plotSamples
        self._ch_start_prev = self._ch_start
        self._ch_stop_prev = self._ch_stop
        self.offset_prev = self.offset
        self.bin_width_prev = self.bin_width
        self._runtime_prev = self._runtime

        self._plot_tab = self.tabs.currentIndex() 
        self.idx = min(len(self.y1), self.plotSamples) 
        self._counts_plotted = False
        self._g2_plotted = False
        self._data_plotted = self._counts_plotted or self._g2_plotted
        self.runtimeCheck = self.runtime_Checkbox.isChecked()
        

    def initUI(self):
        # Apply Global Black & White Theme
        self.setStyleSheet(BLACK_STYLESHEET)
        
        #---------Buttons---------#
        self.liveStart_Button = QtWidgets.QPushButton("Live Start", self)
        self.liveStart_Button.setObjectName("LiveButton") # For CSS targeting
        self.liveStart_Button.clicked.connect(self.liveStart)
        self.liveStart_Button.setEnabled(False)
        self.liveStart_Button.setMinimumHeight(40)

        self.selectLogfile_Button = QtWidgets.QPushButton("Select Logfile", self)
        self.selectLogfile_Button.clicked.connect(self.selectLogfile)
        self.selectLogfile_Button.setEnabled(False)

        self.radio1_Button = QRadioButton("Ch 1", self); self.radio1_Button.setStyleSheet('color: #ff5555;')
        self.radio1_Button.toggled.connect(lambda: self.displayPlot1(self.radio1_Button))

        self.radio2_Button = QRadioButton("Ch 2", self); self.radio2_Button.setStyleSheet('color: #55ff55;')
        self.radio2_Button.toggled.connect(lambda: self.displayPlot2(self.radio2_Button))

        self.radio3_Button = QRadioButton("Ch 3", self); self.radio3_Button.setStyleSheet('color: #5555ff;')
        self.radio3_Button.toggled.connect(lambda: self.displayPlot3(self.radio3_Button))

        self.radio4_Button = QRadioButton("Ch 4", self); self.radio4_Button.setStyleSheet('color: #aaaaaa;')
        self.radio4_Button.toggled.connect(lambda: self.displayPlot4(self.radio4_Button))

        self.runtime_Checkbox = QCheckBox("Enable Timer")
        self.clearCountsDataData_Button = QtWidgets.QPushButton("Clear Plots", self)
        self.clearCountsDataData_Button.clicked.connect(self.clearCountsDataData)
        self.clearg2DataData_Button = QtWidgets.QPushButton("Clear Plots", self)
        self.clearg2DataData_Button.clicked.connect(self.clearg2DataData)

        #---------Labels---------#
        self.logfileText = QtWidgets.QLineEdit('', self)
        self.logfileText.setPlaceholderText("No file selected")
        self.logfileText.setReadOnly(True)

        # --- Monitor Labels (Large) ---
        self.Ch1CountsLabel = QtWidgets.QLabel("0", self)
        self.Ch1CountsLabel.setStyleSheet("color: #ff5555; font-size: 32px; font-weight: bold")
        self.Ch1CountsLabel.setAlignment(QtCore.Qt.AlignCenter)
        
        self.Ch2CountsLabel = QtWidgets.QLabel("0", self)
        self.Ch2CountsLabel.setStyleSheet("color: #55ff55; font-size: 32px; font-weight: bold")
        self.Ch2CountsLabel.setAlignment(QtCore.Qt.AlignCenter)
        
        self.Ch3CountsLabel = QtWidgets.QLabel("0", self)
        self.Ch3CountsLabel.setStyleSheet("color: #5555ff; font-size: 32px; font-weight: bold")
        self.Ch3CountsLabel.setAlignment(QtCore.Qt.AlignCenter)
        
        self.Ch4CountsLabel = QtWidgets.QLabel("0", self)
        self.Ch4CountsLabel.setStyleSheet("color: #aaaaaa; font-size: 32px; font-weight: bold")
        self.Ch4CountsLabel.setAlignment(QtCore.Qt.AlignCenter)

        # Labels for the Counts Tab Sidebar
        self.lbl_mon_1 = QLabel("0", self); self.lbl_mon_1.setStyleSheet("color: #ff5555; font-weight: bold; font-size: 16px")
        self.lbl_mon_2 = QLabel("0", self); self.lbl_mon_2.setStyleSheet("color: #55ff55; font-weight: bold; font-size: 16px")
        self.lbl_mon_3 = QLabel("0", self); self.lbl_mon_3.setStyleSheet("color: #5555ff; font-weight: bold; font-size: 16px")
        self.lbl_mon_4 = QLabel("0", self); self.lbl_mon_4.setStyleSheet("color: #aaaaaa; font-weight: bold; font-size: 16px")

        self.g2RateLabel = QtWidgets.QLabel("Total Pairs: 0")
        self.g2RateLabel.setStyleSheet("font-size: 18px; font-weight: bold; color: #3daee9")
        self.g2RateLabel.setAlignment(QtCore.Qt.AlignCenter)

        self.countdownLabel = QtWidgets.QLabel("00:00:00", self)
        self.countdownLabel.setStyleSheet("color: #ffffff; font-size: 24px; font-family: monospace; font-weight: bold;")
        self.countdownLabel.setAlignment(QtCore.Qt.AlignCenter)

        #---------Interactive Fields---------#
        self.integrationSpinBox = QSpinBox(self)
        self.integrationSpinBox.setRange(0, 65535)
        self.integrationSpinBox.setValue(1000) 
        self.integrationSpinBox.setKeyboardTracking(False) 
        self.integrationSpinBox.valueChanged.connect(self.update_intTime)
        self.integrationSpinBox.setEnabled(False)

        if S15LIB_AVAILABLE:
            try:
                self.dev_list = serial_connection.search_for_serial_devices(tdc1.TimeStampTDC1.DEVICE_IDENTIFIER)
            except:
                pass
        self.devCombobox = QComboBox(self)
        self.devCombobox.addItem('Select your device')
        self.devCombobox.addItems(self.dev_list)
        self.devCombobox.currentTextChanged.connect(self.selectDevice)

        _dev_modes = ['singles', 'pairs', 'g2']
        self.modesCombobox = QComboBox(self)
        self.modesCombobox.addItem('Select mode')
        self.modesCombobox.addItems(_dev_modes)
        self.modesCombobox.currentTextChanged.connect(self.updateDeviceMode)
        self.modesCombobox.setEnabled(False)

        _channels = ['1', '2', '3', '4']
        self.channelsCombobox1 = QComboBox(self)
        self.channelsCombobox1.addItem('Select')
        self.channelsCombobox1.addItems(_channels)
        self.channelsCombobox1.setCurrentIndex(1)
        self.channelsCombobox1.currentTextChanged.connect(self.updateStart)

        self.channelsCombobox2 = QComboBox(self)
        self.channelsCombobox2.addItem('Select')
        self.channelsCombobox2.addItems(_channels)
        self.channelsCombobox2.setCurrentIndex(3)
        self.channelsCombobox2.currentTextChanged.connect(self.updateStop)

        self.samplesSpinbox = QSpinBox(self)
        self.samplesSpinbox.setRange(0, 65535)
        self.samplesSpinbox.setValue(501) 
        self.samplesSpinbox.setKeyboardTracking(False)
        self.samplesSpinbox.valueChanged.connect(self.updateBins)
        self.samplesSpinbox.setEnabled(False)

        self.offsetSpinbox = NoScrollSpinBox(self)
        self.offsetSpinbox.setRange(-10, 65535)
        self.offsetSpinbox.setKeyboardTracking(False)
        self.offsetSpinbox.valueChanged.connect(self.updateOffset)

        self.resolutionSpinbox = NoScrollSpinBox(self)
        self.resolutionSpinbox.setRange(0, 1000)
        self.resolutionSpinbox.setKeyboardTracking(False)
        self.resolutionSpinbox.setValue(2) 
        self.resolutionSpinbox.valueChanged.connect(self.updateBinwidth)

        self.runtimeSpinbox = QSpinBox(self)
        self.runtimeSpinbox.setRange(0, 65535)
        self.runtimeSpinbox.setKeyboardTracking(False)
        self.runtimeSpinbox.setValue(5) 
        self.runtimeSpinbox.valueChanged.connect(self.updateRuntime)
        self.runtimeSpinbox.setEnabled(False)

        _levels = ['NIM (-0.5V)', 'TTL (+1.6V)']
        self.levelsComboBox = QComboBox(self)
        self.levelsComboBox.addItem('Select')
        self.levelsComboBox.addItems(_levels)
        self.levelsComboBox.currentTextChanged.connect(self.updateLevel)
        self.levelsComboBox.setEnabled(False)

        #---------PLOTS---------#
        self.x = []
        self.y1 = []; self.y2 = []; self.y3 = []; self.y4 = []
        self.y_data = [self.y1, self.y2, self.y3, self.y4]

        self.bins = 501
        self.binsize = 2 # nanoseconds
        self.x0 = np.arange(0, self.bins*self.binsize, self.binsize)
        self.y0 = np.zeros_like(self.x0)
        
        # Configure PyQtGraph global options for Black Background
        pg.setConfigOption('background', 'k') # Black background
        pg.setConfigOption('foreground', 'w') # White text/axes
        
        font = QtGui.QFont("Helvetica", 12)
        labelStyle = {'color': '#FFF', 'font-size': '12pt'}

        self.tdcPlot = pg.PlotWidget(title = "Counts Graph")
        self.tdcPlot.setLabel('left', 'Counts', **labelStyle)
        self.tdcPlot.setLabel('bottom', 'Time (s)', **labelStyle)
        self.tdcPlot.showGrid(x=True, y=True, alpha=0.5) # Visible White Grid
        self.tdcPlot.setMinimumHeight(350)
        self.tdcPlot.getAxis('left').setPen('w')
        self.tdcPlot.getAxis('bottom').setPen('w')
        self.tdcPlot.setMouseEnabled(x=False, y=False)
        self.tdcPlot.setYRange(0, 33000) 
        
        self.tdcPlot2 = pg.PlotWidget(title = "Cross Correlation")
        self.tdcPlot2.setLabel('left', 'Correlation', **labelStyle)
        self.tdcPlot2.setLabel('bottom', 'Time Delay (ns)', **labelStyle)
        self.tdcPlot2.showGrid(x=True, y=True, alpha=0.5) # Visible White Grid
        self.tdcPlot2.setMinimumHeight(350)
        self.tdcPlot2.getAxis('left').setPen('w')
        self.tdcPlot2.getAxis('bottom').setPen('w')
        self.tdcPlot2.setMouseEnabled(x=False, y=False)
        self.tdcPlot2.setXRange(0, 100) # Set X range 0 to 100ns

        self.lineStyle1 = pg.mkPen(width=2, color='#ff5555') 
        self.lineStyle2 = pg.mkPen(width=2, color='#55ff55') 
        self.lineStyle3 = pg.mkPen(width=2, color='#5555ff') 
        self.lineStyle4 = pg.mkPen(width=2, color='#aaaaaa') 
        self.lineStyle0 = pg.mkPen(width=1, color='#ff5555')

        self.linePlot1 = self.tdcPlot.plot(self.x, self.y1, pen=self.lineStyle1)
        self.linePlot2 = self.tdcPlot.plot(self.x, self.y2, pen=self.lineStyle2)
        self.linePlot3 = self.tdcPlot.plot(self.x, self.y3, pen=self.lineStyle3)
        self.linePlot4 = self.tdcPlot.plot(self.x, self.y4, pen=self.lineStyle4)
        self.histogramPlot = self.tdcPlot2.plot(self.x0, self.y0, pen=self.lineStyle0, symbol = 'o', symbolPen = '#3daee9', symbolBrush = '#3daee9', symbolSize=3)
        self.linePlots = [self.linePlot1, self.linePlot2, self.linePlot3, self.linePlot4]

        # Timer
        self.timer = QtCore.QTimer()

        self.setWindowTitle("Spin-Q Entanglement Analyzer")
        self.resize(1300, 900) 
        
        # --- TAB SETUP ---
        self.tabs = QTabWidget()
        self.tabs.setFont(QFont("Segoe UI", 12))

        # Tab 1: Counts
        self.tab1 = QWidget()
        t1_layout = QVBoxLayout()
        t1_layout.addWidget(self.tdcPlot)
        t1_controls = QHBoxLayout()
        t1_controls.addWidget(self.clearCountsDataData_Button)
        t1_controls.addStretch()
        t1_layout.addLayout(t1_controls)
        self.tab1.setLayout(t1_layout)
        
        # Tab 2: g2
        self.tab2 = QWidget()
        t2_layout = QVBoxLayout()
        t2_layout.addWidget(self.tdcPlot2)
        t2_controls = QHBoxLayout()
        t2_controls.addWidget(self.g2RateLabel)
        t2_controls.addStretch()
        t2_controls.addWidget(self.clearg2DataData_Button)
        t2_layout.addLayout(t2_controls)
        self.tab2.setLayout(t2_layout)
        
        # Virtual Labs & Analysis (Function now returns a ScrollArea)
        self.tab3 = self.setupVirtualLabTab()
        self.tab4 = self.setupManualCalcTab()
        self.tab5 = self.setupMalusTab()

        self.tabs.addTab(self.tab1, "Live Counts")
        self.tabs.addTab(self.tab2, "Correlation (g2)")
        self.tabs.addTab(self.tab5, "Malus's Law") 
        self.tabs.addTab(self.tab3, "Virtual CHSH") 
        self.tabs.addTab(self.tab4, "Exp. CHSH") 
        
        self.tabs.currentChanged.connect(self.update_plot_tab)

        # --- LAYOUT CONSTRUCTION (SIDEBAR + MAIN) ---
        
        # 1. SIDEBAR (Left)
        sidebarWidget = QWidget()
        sidebarLayout = QVBoxLayout()
        sidebarLayout.setSpacing(15)

        # Device Group
        gbDev = QGroupBox("Connection")
        gbDevLayout = QVBoxLayout()
        gbDevLayout.addWidget(QLabel("Device Path:"))
        gbDevLayout.addWidget(self.devCombobox)
        gbDevLayout.addWidget(QLabel("Operation Mode:"))
        gbDevLayout.addWidget(self.modesCombobox)
        gbDev.setLayout(gbDevLayout)

        # Acquisition Settings Group
        gbAcq = QGroupBox("Acquisition")
        gbAcqLayout = QGridLayout()
        gbAcqLayout.addWidget(QLabel("Integration (ms):"), 0, 0)
        gbAcqLayout.addWidget(self.integrationSpinBox, 0, 1)
        gbAcqLayout.addWidget(QLabel("Plot Samples:"), 1, 0)
        gbAcqLayout.addWidget(self.samplesSpinbox, 1, 1)
        gbAcqLayout.addWidget(QLabel("Logic Level:"), 2, 0)
        gbAcqLayout.addWidget(self.levelsComboBox, 2, 1)
        gbAcq.setLayout(gbAcqLayout)

        # g2 Settings (Conditional)
        self.g2Groupbox = QGroupBox("g2 Parameters")
        gbG2Layout = QGridLayout()
        gbG2Layout.addWidget(QLabel("Start Ch:"), 0, 0)
        gbG2Layout.addWidget(self.channelsCombobox1, 0, 1)
        gbG2Layout.addWidget(QLabel("Stop Ch:"), 1, 0)
        gbG2Layout.addWidget(self.channelsCombobox2, 1, 1)
        gbG2Layout.addWidget(QLabel("Offset (ns):"), 2, 0)
        gbG2Layout.addWidget(self.offsetSpinbox, 2, 1)
        gbG2Layout.addWidget(QLabel("Bin (ns):"), 3, 0)
        gbG2Layout.addWidget(self.resolutionSpinbox, 3, 1)
        self.g2Groupbox.setLayout(gbG2Layout)

        # Timer (Fixed Layout - Multi-line)
        gbTime = QGroupBox("Timer")
        gbTimeLayout = QVBoxLayout()
        
        # Row 1: Controls
        timeRow1 = QHBoxLayout()
        timeRow1.addWidget(self.runtime_Checkbox)
        timeRow1.addWidget(self.runtimeSpinbox)
        timeRow1.addWidget(QLabel("min"))
        gbTimeLayout.addLayout(timeRow1)
        
        # Row 2: Display
        gbTimeLayout.addWidget(self.countdownLabel)
        
        gbTime.setLayout(gbTimeLayout)

        # Logging
        gbLog = QGroupBox("Data Logging")
        gbLogLayout = QVBoxLayout()
        gbLogLayout.addWidget(self.logfileText)
        gbLogLayout.addWidget(self.selectLogfile_Button)
        gbLog.setLayout(gbLogLayout)

        # Plot Controls
        self.countsGroupbox = QGroupBox("Plot Visibility")
        pcLayout = QGridLayout()
        pcLayout.addWidget(self.radio1_Button, 0, 0)
        pcLayout.addWidget(self.radio2_Button, 0, 1)
        pcLayout.addWidget(self.radio3_Button, 1, 0)
        pcLayout.addWidget(self.radio4_Button, 1, 1)
        self.countsGroupbox.setLayout(pcLayout)

        # Add to Sidebar
        sidebarLayout.addWidget(self.liveStart_Button) # Big button at top
        sidebarLayout.addWidget(gbDev)
        sidebarLayout.addWidget(gbAcq)
        sidebarLayout.addWidget(self.g2Groupbox)
        sidebarLayout.addWidget(self.countsGroupbox)
        sidebarLayout.addWidget(gbTime)
        sidebarLayout.addWidget(gbLog)
        sidebarLayout.addStretch() # Push everything up

        sidebarWidget.setLayout(sidebarLayout)
        sidebarWidget.setFixedWidth(280)

        # Wrap sidebar in ScrollArea for small screens
        sbScroll = QScrollArea()
        sbScroll.setWidget(sidebarWidget)
        sbScroll.setWidgetResizable(True)
        sbScroll.setFixedWidth(300)
        sbScroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # 2. MAIN CONTENT (Right)
        mainContent = QWidget()
        mainLayout = QVBoxLayout()

        # Top: Live Monitor Dashboard
        monitorFrame = QFrame()
        monitorFrame.setStyleSheet("background-color: #000000; border-radius: 8px; border: 1px solid #ffffff;")
        monLayout = QHBoxLayout()
        
        for lbl, title in [(self.Ch1CountsLabel, "Ch 1"), (self.Ch2CountsLabel, "Ch 2"), (self.Ch3CountsLabel, "Ch 3"), (self.Ch4CountsLabel, "Ch 4")]:
            v = QVBoxLayout()
            t = QLabel(title)
            t.setStyleSheet("color: #ffffff; font-size: 14px;")
            t.setAlignment(Qt.AlignCenter)
            v.addWidget(t)
            v.addWidget(lbl)
            monLayout.addLayout(v)
            if title != "Ch 4": # Divider
                line = QFrame()
                line.setFrameShape(QFrame.VLine); line.setStyleSheet("color: #ffffff;")
                monLayout.addWidget(line)

        monitorFrame.setLayout(monLayout)
        monitorFrame.setMaximumHeight(100)
        
        # Bottom: Global HWP Control (Persistent)
        self.hwpGlobalGroup = QGroupBox("Global Source Control (Half-Wave Plate)")
        self.hwpGlobalGroup.setStyleSheet("background-color: #000000;")
        hwpLayout = QHBoxLayout()
        self.virt_sliderHWP = QSlider(Qt.Horizontal)
        self.virt_sliderHWP.setRange(0, 900)
        self.virt_sliderHWP.setValue(0)
        self.virt_sliderHWP.valueChanged.connect(lambda v: self.virt_spinHWP.setValue(v / 10.0))
        self.virt_spinHWP = QDoubleSpinBox()
        self.virt_spinHWP.setRange(0.0, 90.0)
        self.virt_spinHWP.setValue(0.0)
        self.virt_spinHWP.setSingleStep(0.5)
        self.virt_spinHWP.valueChanged.connect(lambda v: self.virt_sliderHWP.setValue(int(v * 10)))
        self.virt_spinHWP.valueChanged.connect(self.updateQuantumStateLabel)
        self.virt_spinHWP.valueChanged.connect(self.updateSchematicAngles)
        hwpLayout.addWidget(QLabel("HWP Angle:"))
        hwpLayout.addWidget(self.virt_sliderHWP)
        hwpLayout.addWidget(self.virt_spinHWP)
        self.hwpGlobalGroup.setLayout(hwpLayout)

        mainLayout.addWidget(monitorFrame)
        mainLayout.addWidget(self.tabs)
        mainLayout.addWidget(self.hwpGlobalGroup)
        mainContent.setLayout(mainLayout)

        # 3. ROOT LAYOUT
        rootLayout = QHBoxLayout()
        rootLayout.addWidget(sbScroll)
        rootLayout.addWidget(mainContent)
        
        centralWidget = QWidget()
        centralWidget.setLayout(rootLayout)
        self.setCentralWidget(centralWidget)


    # --- Real Experiment Analysis Tab Methods (Scrollable) ---
    def setupManualCalcTab(self):
        # 1. Create the Scroll Area
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        
        # 2. Create the Widget that holds contents
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setSpacing(20) # Add space between elements

        header = QLabel("Real Experiment Data Analysis")
        header.setStyleSheet("font-size: 20px; font-weight: bold; color: #3daee9;")
        layout.addWidget(header)
        
        instr = QLabel("Manually input coincidence counts measured from your real experiment for the four standard CHSH settings.")
        instr.setWordWrap(True)
        instr.setStyleSheet("color: #ffffff;")
        layout.addWidget(instr)
        
        # Monitor Row
        hwpRefGroup = QGroupBox("HWP Status Monitor")
        hwpRefLayout = QHBoxLayout()
        lbl_hwp_angle = QLabel("HWP Angle: 0.0°")
        lbl_hwp_state = QLabel("State: |HH> (Separable)")
        lbl_hwp_state.setStyleSheet("color: #3daee9; font-weight: bold;")
        hwpRefLayout.addWidget(lbl_hwp_angle)
        hwpRefLayout.addWidget(lbl_hwp_state)
        hwpRefGroup.setLayout(hwpRefLayout)
        self.hwp_angle_labels.append(lbl_hwp_angle)
        self.hwp_state_labels.append(lbl_hwp_state)
        layout.addWidget(hwpRefGroup)

        self.manual_inputs = {}
        self.virt_comparison_labels = {} 

        grid = QGridLayout()
        grid.setSpacing(15)

        # Settings configuration: key, label, baseA, baseB
        settings_data = [
            ('e1', 'Setting 1 (E1)', 0, 22.5),
            ('e2', 'Setting 2 (E2)', 0, 67.5),
            ('e3', 'Setting 3 (E3)', 45, 22.5),
            ('e4', 'Setting 4 (E4)', 45, 67.5)
        ]

        row = 0
        col = 0
        for key, title, baseA, baseB in settings_data:
            group = QGroupBox(f"{title}")
            group_layout = QGridLayout()

            spin_pp = NoScrollSpinBox(); spin_pp.setRange(0, 999999); spin_pp.valueChanged.connect(self.updateManualCalc)
            spin_mm = NoScrollSpinBox(); spin_mm.setRange(0, 999999); spin_mm.valueChanged.connect(self.updateManualCalc)
            spin_pm = NoScrollSpinBox(); spin_pm.setRange(0, 999999); spin_pm.valueChanged.connect(self.updateManualCalc)
            spin_mp = NoScrollSpinBox(); spin_mp.setRange(0, 999999); spin_mp.valueChanged.connect(self.updateManualCalc)

            lbl_pp = QLabel(f"N++ (A={baseA}, B={baseB})")
            lbl_pm = QLabel(f"N+- (A={baseA}, B={baseB+90})")
            lbl_mp = QLabel(f"N-+ (A={baseA+90}, B={baseB})")
            lbl_mm = QLabel(f"N-- (A={baseA+90}, B={baseB+90})")

            for lbl in [lbl_pp, lbl_pm, lbl_mp, lbl_mm]:
                lbl.setAlignment(Qt.AlignCenter)
                lbl.setStyleSheet("color: #ffffff; font-size: 11px;")

            group_layout.addWidget(lbl_pp, 0, 0); group_layout.addWidget(spin_pp, 1, 0)
            group_layout.addWidget(lbl_pm, 0, 1); group_layout.addWidget(spin_pm, 1, 1)
            group_layout.addWidget(lbl_mp, 2, 0); group_layout.addWidget(spin_mp, 3, 0)
            group_layout.addWidget(lbl_mm, 2, 1); group_layout.addWidget(spin_mm, 3, 1)

            e_res = QLabel("E = ---")
            e_res.setStyleSheet("font-weight: bold; font-size: 16px; color: #fff;")
            e_res.setAlignment(Qt.AlignCenter)
            group_layout.addWidget(e_res, 4, 0, 1, 2)
            
            lbl_virt_ref = QLabel("Virtual E: ---")
            lbl_virt_ref.setStyleSheet("color: #888; font-style: italic;")
            lbl_virt_ref.setAlignment(Qt.AlignCenter)
            group_layout.addWidget(lbl_virt_ref, 5, 0, 1, 2)
            
            group.setLayout(group_layout)
            grid.addWidget(group, row, col)
            self.virt_comparison_labels[key] = lbl_virt_ref
            self.manual_inputs[key] = [spin_pp, spin_mm, spin_pm, spin_mp, e_res]
            
            col += 1
            if col > 1:
                col = 0
                row += 1

        layout.addLayout(grid)

        # S Calculation Result
        s_frame = QFrame()
        s_frame.setStyleSheet("background-color: #111; border-radius: 5px; border: 1px solid #ffffff; margin-top: 15px;")
        s_frame_layout = QVBoxLayout(s_frame) 

        real_s_layout = QHBoxLayout()
        s_label_title = QLabel("Final CHSH Parameter S:")
        s_label_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #3daee9;")
        self.manual_s_label = QLabel("---")
        self.manual_s_label.setStyleSheet("font-size: 32px; font-weight: bold; color: gray;")
        real_s_layout.addWidget(s_label_title)
        real_s_layout.addStretch()
        real_s_layout.addWidget(self.manual_s_label)
        
        self.virt_s_comparison_label = QLabel("Virtual S: ---")
        self.virt_s_comparison_label.setStyleSheet("font-size: 14px; color: #aaa;")
        
        s_frame_layout.addLayout(real_s_layout)
        s_frame_layout.addWidget(self.virt_s_comparison_label, alignment=Qt.AlignRight)

        layout.addWidget(s_frame)
        layout.addStretch() # Push up

        scroll.setWidget(content_widget)
        return scroll

    def updateManualCalc(self):
        e_vals = []
        e_errs = []

        for key in ['e1', 'e2', 'e3', 'e4']:
            inputs = self.manual_inputs[key]
            n_pp = inputs[0].value() 
            n_mm = inputs[1].value() 
            n_pm = inputs[2].value() 
            n_mp = inputs[3].value() 
            label = inputs[4]

            n_corr = n_pp + n_mm
            n_anti = n_pm + n_mp
            total = n_corr + n_anti

            if total > 0:
                e = (n_corr - n_anti) / total
                try:
                    dE = (2 * math.sqrt(n_corr * n_anti)) / (total ** 1.5)
                except ValueError:
                    dE = 0.0

                label.setText(f"{e:.4f} ± {dE:.4f}")
                
                if e > 0: 
                    label.setStyleSheet("color: #55ff55; font-weight: bold; font-size: 16px;")
                else: 
                    label.setStyleSheet("color: #ff5555; font-weight: bold; font-size: 16px;")
                
                e_vals.append(e)
                e_errs.append(dE)
            else:
                label.setText("---")
                e_vals.append(None)
                e_errs.append(0.0)

        if all(v is not None for v in e_vals):
            s = e_vals[0] - e_vals[1] + e_vals[2] + e_vals[3]
            s_err = math.sqrt(sum([err**2 for err in e_errs]))

            self.manual_s_label.setText(f"{s:.4f} ± {s_err:.4f}")
            
            if abs(s) > 2:
                self.manual_s_label.setStyleSheet("font-size: 32px; font-weight: bold; color: #55ff55;")
            else:
                self.manual_s_label.setStyleSheet("font-size: 32px; font-weight: bold; color: #ff5555;")
        else:
            self.manual_s_label.setText("---")
            self.manual_s_label.setStyleSheet("font-size: 32px; font-weight: bold; color: gray;")

    def updateComparisonLogic(self):
        v_e1 = self.virt_notebook['e1']['val']
        v_e2 = self.virt_notebook['e2']['val']
        v_e3 = self.virt_notebook['e3']['val']
        v_e4 = self.virt_notebook['e4']['val']
        
        for k in ['e1', 'e2', 'e3', 'e4']:
            val = self.virt_notebook[k]['val']
            if val is not None:
                self.virt_comparison_labels[k].setText(f"Virtual E: {val:.3f}")
            else:
                self.virt_comparison_labels[k].setText("Virtual E: ---")
                
        if all(v is not None for v in [v_e1, v_e2, v_e3, v_e4]):
            v_s = v_e1 - v_e2 + v_e3 + v_e4
            self.virt_s_comparison_label.setText(f"Virtual S: {v_s:.3f}")
        else:
             self.virt_s_comparison_label.setText("Virtual S: ---")

    # --- Malus Law Setup Method (Scrollable) ---
    def setupMalusTab(self):
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        content_widget = QWidget()
        scroll.setWidget(content_widget)
        
        layout = QVBoxLayout(content_widget)
        layout.setSpacing(20)
        
        header = QLabel("Verification of Malus's Law")
        header.setStyleSheet("font-size: 20px; font-weight: bold; color:#3daee9;")
        layout.addWidget(header)

        # Schematic
        self.malus_schematic = MalusSchematic()
        layout.addWidget(self.malus_schematic)

        intro = QLabel("Malus's Law states that when a perfect polarizer is placed in a polarized beam of light, the intensity, I, of the light that passes through is given by I = I₀ cos²(θ).")
        intro.setWordWrap(True)
        intro.setStyleSheet("color: #ffffff; margin-bottom: 5px;")
        layout.addWidget(intro)
        
        # --- Experiment Controls (Moved Here) ---
        controlsGroup = QGroupBox("Experiment Controls")
        controlsLayout = QHBoxLayout()
        
        controlsLayout.addWidget(QLabel("Polarizer Angle (θ):"))
        self.malus_slider = QSlider(Qt.Horizontal)
        self.malus_slider.setRange(0, 3600) 
        self.malus_slider.setValue(0)
        self.malus_slider.valueChanged.connect(lambda v: self.malus_spin.setValue(v / 10.0))
        
        self.malus_spin = QDoubleSpinBox()
        self.malus_spin.setRange(0.0, 360.0)
        self.malus_spin.setValue(0.0)
        self.malus_spin.setSingleStep(0.5)
        self.malus_spin.valueChanged.connect(lambda v: self.malus_slider.setValue(int(v * 10)))
        self.malus_spin.valueChanged.connect(self.malus_schematic.set_angle)
        # Update normalized plot in real time if spinbox moves (optional)
        self.malus_spin.valueChanged.connect(self.updateMalusNormPlot)

        controlsLayout.addWidget(self.malus_slider)
        controlsLayout.addWidget(self.malus_spin)
        
        controlsGroup.setLayout(controlsLayout)
        layout.addWidget(controlsGroup)

        # Monitor (HWP)
        hwpRefGroup = QGroupBox("HWP Status Monitor")
        hwpRefLayout = QHBoxLayout()
        lbl_hwp_angle = QLabel("HWP Angle: 0.0°")
        lbl_hwp_state = QLabel("State: |HH> (Separable)")
        lbl_hwp_state.setStyleSheet("color: #3daee9; font-weight: bold;")
        hwpRefLayout.addWidget(lbl_hwp_angle)
        hwpRefLayout.addWidget(lbl_hwp_state)
        hwpRefGroup.setLayout(hwpRefLayout)
        self.hwp_angle_labels.append(lbl_hwp_angle)
        self.hwp_state_labels.append(lbl_hwp_state)
        layout.addWidget(hwpRefGroup)
        
        # --- Bottom Area: Data Table & Normalized Plot ---
        bottomLayout = QHBoxLayout()
        
        # Left: Table
        tableGroup = QGroupBox("Data Recording")
        tableLayout = QVBoxLayout()
        self.malus_table = QTableWidget()
        self.malus_table.setColumnCount(2)
        self.malus_table.setHorizontalHeaderLabels(["Angle (°)", "Counts (cps)"])
        self.malus_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.malus_table.setMinimumHeight(250)
        
        angles = list(range(0, 181, 15))
        self.malus_table.setRowCount(len(angles))
        for i, angle in enumerate(angles):
            item_angle = QTableWidgetItem(str(angle))
            item_angle.setFlags(item_angle.flags() ^ Qt.ItemIsEditable) 
            self.malus_table.setItem(i, 0, item_angle)
            self.malus_table.setItem(i, 1, QTableWidgetItem(""))
            
        self.malus_table.cellChanged.connect(self.updateMalusNormPlot)
        
        tableLayout.addWidget(self.malus_table)
        tableGroup.setLayout(tableLayout)
        
        # Right: Normalized Plot
        plotGroup = QGroupBox("Normalized Data Analysis")
        plotLayout = QVBoxLayout()
        self.malus_norm_plot = pg.PlotWidget(title="Normalized Intensity vs Angle")
        self.malus_norm_plot.setLabel('left', 'Normalized Intensity')
        self.malus_norm_plot.setLabel('bottom', 'Angle (degrees)')
        self.malus_norm_plot.setYRange(0, 1.1)
        self.malus_norm_plot.setXRange(0, 180)
        self.malus_norm_plot.setMinimumHeight(250) 
        self.malus_norm_plot.showGrid(x=True, y=True, alpha=0.5)
        self.malus_norm_plot.getAxis('left').setPen('w')
        self.malus_norm_plot.getAxis('bottom').setPen('w')
        self.malus_norm_plot.setMouseEnabled(x=False, y=False)
        
        theo_x = np.linspace(0, 360, 361)
        rad_x = np.radians(theo_x)
        theo_y = (np.cos(rad_x)**2)
        self.malus_norm_plot.plot(theo_x, theo_y, pen=pg.mkPen(color=(255, 100, 100, 80), width=4), name="Theory")
        
        self.malus_user_curve = self.malus_norm_plot.plot(pen=None, symbol='o', symbolBrush='#55ff55', symbolSize=8, name="User Data")
        
        plotLayout.addWidget(self.malus_norm_plot)
        plotGroup.setLayout(plotLayout)
        
        bottomLayout.addWidget(tableGroup, 1)
        bottomLayout.addWidget(plotGroup, 2)
        
        layout.addLayout(bottomLayout)
        
        return scroll 

    def updateMalusRate(self):
        if not self.malus_laserOn:
            return
            
        theta = self.malus_spin.value()
        rad = math.radians(theta)
        intensity = math.cos(rad) ** 2
        
        I0 = 500
        dark_counts = 20
        rate = I0 * intensity + dark_counts
        
        noise = math.sqrt(rate) * (random.random() - 0.5)
        final_rate = max(0, int(rate + noise))
        self.current_malus_rate = final_rate 
        
        self.malus_rateLabel.setText(f"{final_rate} cps")

    def updateMalusNormPlot(self):
        x_vals = []
        y_vals = []
        
        rows = self.malus_table.rowCount()
        for r in range(rows):
            item_cnt = self.malus_table.item(r, 1)
            if item_cnt and item_cnt.text().strip():
                try:
                    val = float(item_cnt.text())
                    angle = float(self.malus_table.item(r, 0).text())
                    x_vals.append(angle)
                    y_vals.append(val)
                except ValueError:
                    pass
        
        if not y_vals:
            self.malus_user_curve.setData([], [])
            return
            
        max_val = max(y_vals)
        if max_val == 0: max_val = 1
        
        norm_y = [y / max_val for y in y_vals]
        
        self.malus_user_curve.setData(x_vals, norm_y)


    # --- Virtual Lab Setup Method (Scrollable) ---
    def setupVirtualLabTab(self):
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        content_widget = QWidget()
        scroll.setWidget(content_widget)
        
        layout = QVBoxLayout(content_widget)
        layout.setSpacing(15)

        headerLayout = QHBoxLayout()
        title = QLabel("Virtual Quantum Optics Lab - CHSH Test")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #3daee9;")
        headerLayout.addWidget(title)
        headerLayout.addStretch()
        layout.addLayout(headerLayout)

        # Schematic
        self.optical_schematic = OpticalSchematic()
        layout.addWidget(self.optical_schematic)
        
        intro = QLabel("Simulate a Bell test experiment using the CHSH inequality. Control the polarization angles for Alice and Bob.")
        intro.setWordWrap(True)
        intro.setStyleSheet("color: #ffffff; margin-bottom: 10px;")
        layout.addWidget(intro)
        
        # Notebook (Moved Up)
        notebookGroup = QGroupBox("CHSH Notebook")
        nbLayout = QGridLayout()
        nbLayout.setVerticalSpacing(10)

        nbLayout.addWidget(QLabel("Measurement"), 0, 0)
        nbLayout.addWidget(QLabel("Preset Angles"), 0, 1)
        nbLayout.addWidget(QLabel("Result (E)"), 0, 2)
        nbLayout.addWidget(QLabel("Action"), 0, 3)

        self.virt_resLabels = {}
        for i, key in enumerate(['e1', 'e2', 'e3', 'e4']):
            row = i + 1
            data = self.virt_notebook[key]
            nbLayout.addWidget(QLabel(f"{key.upper()} ({data['label']})"), row, 0)

            presetBtn = QPushButton("Set Angles")
            presetBtn.clicked.connect(lambda _, k=key: self.setVirtualAngles(k))
            nbLayout.addWidget(presetBtn, row, 1)

            resLbl = QLabel("---")
            resLbl.setStyleSheet("font-weight: bold;")
            nbLayout.addWidget(resLbl, row, 2)
            self.virt_resLabels[key] = resLbl

            measureBtn = QPushButton("Acquire")
            measureBtn.clicked.connect(lambda _, k=key: self.measureVirtualE(k))
            nbLayout.addWidget(measureBtn, row, 3)

        notebookGroup.setLayout(nbLayout)
        layout.addWidget(notebookGroup)

        # Monitor (Moved Down)
        hwpGroup = QGroupBox("HWP Status Monitor")
        hwpLayout = QHBoxLayout()
        self.virt_stateLabel = QLabel("Source State: |HH> (Separable)")
        self.virt_stateLabel.setStyleSheet("color: #3daee9; font-weight: bold; font-size: 16px;")
        self.virt_angleLabel = QLabel("HWP Angle: 0.0°")
        self.virt_angleLabel.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 16px;")
        
        self.hwp_state_labels.append(self.virt_stateLabel)
        self.hwp_angle_labels.append(self.virt_angleLabel)
        
        hwpLayout.addWidget(self.virt_angleLabel)
        hwpLayout.addWidget(self.virt_stateLabel)
        hwpGroup.setLayout(hwpLayout)
        layout.addWidget(hwpGroup)

        # Config (Simplified - Rate removed)
        configGroup = QGroupBox("Configuration")
        configLayout = QHBoxLayout()
        self.virt_configLabel = QLabel("A = 0.0°   |   B = 0.0°")
        self.virt_configLabel.setStyleSheet("font-size: 20px; color: #fff; font-weight: bold;")
        configLayout.addWidget(self.virt_configLabel)
        configGroup.setLayout(configLayout)
        layout.addWidget(configGroup)

        # S Label
        sLayout = QHBoxLayout()
        self.virt_sLabel = QLabel("S = ---")
        self.virt_sLabel.setStyleSheet("font-size: 24px; font-weight: bold; color: #fff;")
        sLayout.addStretch()
        sLayout.addWidget(self.virt_sLabel)
        sLayout.addStretch()
        layout.addLayout(sLayout)
        layout.addStretch()
        
        return scroll

    def updateQuantumStateLabel(self, val):
        state_str = "Source State: Elliptical/Mixed"
        if abs(val - 0) < 1.0:
            state_str = "Source State: |HH> (Separable)"
        elif abs(val - 22.5) < 1.0:
            state_str = "Source State: (|HH> + |VV>)/√2 (Entangled)"
        elif abs(val - 45.0) < 1.0:
            state_str = "Source State: |VV> (Separable)"
            
        for lbl_angle in self.hwp_angle_labels:
            lbl_angle.setText(f"HWP Angle: {val:.1f}°")
            
        for lbl_state in self.hwp_state_labels:
            lbl_state.setText(state_str)

    def updateSchematicAngles(self):
        if hasattr(self, 'optical_schematic'):
            hwp = self.virt_spinHWP.value()
            self.optical_schematic.set_angles(hwp, self.virt_current_A, self.virt_current_B)

    # --- Virtual Lab Logic ---
    def calculateVirtualRate(self, angleA, angleB):
        if not self.virt_laserOn: return 0
        hwp_angle = self.virt_spinHWP.value()
        theta_p = math.radians(2 * hwp_angle)
        radA = math.radians(angleA)
        radB = math.radians(angleB)
        amp = math.cos(theta_p) * math.cos(radA) * math.cos(radB) + \
              math.sin(theta_p) * math.sin(radA) * math.sin(radB)
        prob = amp ** 2
        scaled_prob = 2 * prob 
        signal = self.virt_MAX_COUNTS * (self.virt_VISIBILITY * scaled_prob + (1 - self.virt_VISIBILITY) / 4)
        rate = signal + self.virt_DARK_COUNTS
        noise = math.sqrt(rate) * (random.random() - 0.5)
        return max(0, int(rate + noise))

    def setVirtualAngles(self, key):
        current_hwp = self.virt_spinHWP.value()
        if abs(current_hwp - 22.5) > 0.1: 
            QMessageBox.warning(self, "HWP Alignment Error", 
                "The Half Wave Plate (HWP) must be set to exactly 22.5° to align the system for this experiment.")
            return

        data = self.virt_notebook[key]
        self.virt_current_A = data['a']
        self.virt_current_B = data['b']
        self.virt_configLabel.setText(f"A = {self.virt_current_A}°   |   B = {self.virt_current_B}°")
        self.virt_configLabel.setStyleSheet("font-size: 20px; color: #55ff55; font-weight: bold;")
        QtCore.QTimer.singleShot(500, lambda: self.virt_configLabel.setStyleSheet("font-size: 20px; color: #fff; font-weight: bold;"))
        self.updateSchematicAngles()

    def measureVirtualE(self, key):
        a = self.virt_current_A
        b = self.virt_current_B
        
        n_pp = self.calculateVirtualRate(a, b)
        n_pm = self.calculateVirtualRate(a, b + 90)
        n_mp = self.calculateVirtualRate(a + 90, b)
        n_mm = self.calculateVirtualRate(a + 90, b + 90)
        
        n_corr = n_pp + n_mm
        n_anti = n_pm + n_mp
        total = n_corr + n_anti
        
        if total == 0: total = 1
        E = (n_corr - n_anti) / total

        try:
            dE = (2 * math.sqrt(n_corr * n_anti)) / (total ** 1.5)
        except ValueError:
            dE = 0.0

        self.virt_notebook[key]['val'] = E
        self.virt_notebook[key]['err'] = dE 
        
        lbl = self.virt_resLabels[key]
        lbl.setText(f"{E:.3f} ± {dE:.3f}")
        
        if E > 0: lbl.setStyleSheet("color: #55ff55; font-weight: bold;")
        else: lbl.setStyleSheet("color: #ff5555; font-weight: bold;")
        
        self.calculateVirtualS()

    def calculateVirtualS(self):
        vals = [self.virt_notebook[k]['val'] for k in ['e1', 'e2', 'e3', 'e4']]
        errs = [self.virt_notebook[k].get('err', 0.0) for k in ['e1', 'e2', 'e3', 'e4']]
        
        if any(v is None for v in vals): return
        S = vals[0] - vals[1] + vals[2] + vals[3]
        S_err = math.sqrt(sum([e**2 for e in errs]))
        self.virt_sLabel.setText(f"S = {S:.3f} ± {S_err:.3f}")
        
        if abs(S) > 2:
            self.virt_sLabel.setStyleSheet("font-size: 24px; font-weight: bold; color: #55ff55;")
        else:
            self.virt_sLabel.setStyleSheet("font-size: 24px; font-weight: bold; color: #ff5555;")


    @QtCore.pyqtSlot(str)
    def selectDevice(self, devPath: str):
        if devPath == 'Select your device':
            return
        if self.acq_flag == False:
            self.StrongResetInternalVariables()
            self.resetGUIelements()
            print('Creating TDC1 object.')
            try:
                self._tdc1_dev = tdc1.TimeStampTDC1(devPath)
                self._dev_path = devPath
                check = self._tdc1_dev._device_path
                print(f'Device connected at {check}')
                self.enableDevOptions()
                self._dev_selected = True
            except Exception as e:
                print(f"Failed to connect: {e}")
                
        elif self.acq_flag == True:
            msgBox = QtWidgets.QMessageBox()
            msgBox.setIcon(QtWidgets.QMessageBox.Information)
            msgBox.setText('Data is currently being collected. Stop first.')
            msgBox.setWindowTitle('Error Selecting Device')
            msgBox.setStandardButtons(QMessageBox.Ok)
            msgBox.exec()
            self.modesCombobox.setCurrentText(self._dev_mode_prev)

    @QtCore.pyqtSlot()
    def updateDevList(self):
        self.devCombobox.clear()
        self.devCombobox.addItem('Select your device')
        if S15LIB_AVAILABLE:
            devices = serial_connection.search_for_serial_devices(tdc1.TimeStampTDC1.DEVICE_IDENTIFIER)
            self.devCombobox.addItems(devices)

    @QtCore.pyqtSlot(str)
    def updateDeviceMode(self, newMode: str):
        if newMode == 'Select mode': 
            pass
        elif self._dev_selected == True and self.acq_flag == False and self._data_plotted == True: 
            msgBox = QtWidgets.QMessageBox()
            msgBox.setIcon(QtWidgets.QMessageBox.Information)
            msgBox.setText('Any unsaved data will be lost. Confirm change?')
            msgBox.setWindowTitle('Confirm Device Mode Change')
            msgBox.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
            returnValue = msgBox.exec()
            if returnValue == QMessageBox.Ok:
                self.deleteWorkerAndThread()
                self.selectLogfile_Button.setText('Select Logfile')
                self.logfileText.setText('')
                self.log_flag = False
                self.acq_flag = False
                if self._tdc1_dev == None:
                    self._tdc1_dev = tdc1.TimeStampTDC1(self._dev_path)
                if newMode == 'g2':
                    self._tdc1_dev.mode = 'timestamp'
                    self.samplesSpinbox.setEnabled(True)
                else:
                    self._tdc1_dev.mode = newMode 
                self._dev_mode = newMode
                print(f'Device at {self._dev_path} is now in {self._dev_mode} mode')
                if newMode == 'singles':
                    self.samplesSpinbox.setEnabled(False)
                if newMode == 'pairs':
                    self.samplesSpinbox.setEnabled(True)
            elif returnValue == QMessageBox.Cancel:
                self.modesCombobox.setCurrentText(self._dev_mode_prev)
        elif self._dev_selected == True and self.acq_flag == False and self._data_plotted == False:
            if self._tdc1_dev == None:
                    self._tdc1_dev = tdc1.TimeStampTDC1(self._dev_path)
            if newMode == 'g2':
                self._tdc1_dev.mode = 'timestamp'
                self.samplesSpinbox.setEnabled(True)
            else:
                self._tdc1_dev.mode = newMode
            self._dev_mode = newMode
            print(f'Device at {self._dev_path} is now in {self._dev_mode} mode')
            if newMode == 'singles':
                    self.samplesSpinbox.setEnabled(False)
            if newMode == 'pairs':
                self.samplesSpinbox.setEnabled(True)
        elif self._dev_selected == False:
            print('Please select a device first')
        
    @QtCore.pyqtSlot('PyQt_PyObject')
    def closethreads_ports_timers(self, dev):
        self.stopTimer()
        self.acq_flag = False
        self.modesCombobox.setEnabled(True)
        self.levelsComboBox.setEnabled(True)
        self.devCombobox.setEnabled(True)
        self.runtimeSpinbox.setEnabled(True)
        self.runtime_Checkbox.setEnabled(True)
        self.selectLogfile_Button.setEnabled(True)
        self.liveStart_Button.setText("Live Start")
        self.liveStart_Button.setProperty("active", False)
        self.liveStart_Button.style().unpolish(self.liveStart_Button)
        self.liveStart_Button.style().polish(self.liveStart_Button)

    @QtCore.pyqtSlot('PyQt_PyObject')
    def logfile_permission_error_reset(self, dev):
        msgBox = QtWidgets.QMessageBox()
        msgBox.setIcon(QtWidgets.QMessageBox.Critical)
        msgBox.setText('Ensure logfile is not open in another program.')
        msgBox.setWindowTitle('Permission Error')
        msgBox.setStandardButtons(QMessageBox.Ok)
        msgBox.exec()
        self.stopTimer()
        self.acq_flag = False
        self.modesCombobox.setEnabled(True)
        self.levelsComboBox.setEnabled(True)
        self.devCombobox.setEnabled(True)
        self.runtimeSpinbox.setEnabled(True)
        self.runtime_Checkbox.setEnabled(True)
        self.selectLogfile_Button.setEnabled(True)
        self.liveStart_Button.setText("Live Start")
        self.liveStart_Button.setProperty("active", False)
        self.liveStart_Button.style().unpolish(self.liveStart_Button)
        self.liveStart_Button.style().polish(self.liveStart_Button)

    @QtCore.pyqtSlot()
    def update_plot_tab(self):
        self._plot_tab = self.tabs.currentIndex()
        if self.tabs.tabText(self._plot_tab) == "Exp. CHSH":
            self.updateComparisonLogic()

    @QtCore.pyqtSlot(int)
    def update_intTime(self, int_time: int):
        self.integration_time = int_time * 1e-3
        if self.logger:
            self.logger.int_time = int_time * 1e-3

    @QtCore.pyqtSlot(int)
    def updateBins(self, bins: int):
        self.bins = bins
        if self.logger:
            self.logger.bins = bins

    @QtCore.pyqtSlot(int)
    def updateOffset(self, offset: int):
        self.offset = offset
        if self.logger:
            self.logger.offset = offset

    @QtCore.pyqtSlot()
    def liveStart(self):
        if self.modesCombobox.currentText() == "Select mode":
            msgBox = QtWidgets.QMessageBox()
            msgBox.setIcon(QtWidgets.QMessageBox.Information)
            msgBox.setText('Please select a GUI mode.')
            msgBox.setWindowTitle('GUI mode?')
            msgBox.setStandardButtons(QMessageBox.Ok)
            msgBox.exec()
            return
        if self.acq_flag is True and self.liveStart_Button.text() == "Live Stop":
            self.endRun()
            self.modesCombobox.setEnabled(True)
            self.levelsComboBox.setEnabled(True)
            self.devCombobox.setEnabled(True)
            self.runtimeSpinbox.setEnabled(True)
            self.runtime_Checkbox.setEnabled(True)
            if self._tdc1_dev: self._tdc1_dev._com.reset_input_buffer()
        elif self.acq_flag is False and self.liveStart_Button.text() == "Live Start":
            self.liveStart_Button.setEnabled(False)
            QtCore.QTimer.singleShot(1000, lambda: self.liveStart_Button.setEnabled(True))
            if self._tdc1_dev == None:
                self._tdc1_dev = tdc1.TimeStampTDC1(self.devCombobox.currentText())
            self.acq_flag = True
            if self._data_plotted == True:
                if self.modesCombobox.currentText() == 'g2' and self._g2_plotted == True:
                    msgBox = QtWidgets.QMessageBox()
                    msgBox.setIcon(QtWidgets.QMessageBox.Information)
                    msgBox.setText('A g2 plot already exists. Clear the old plot and start anew?')
                    msgBox.setWindowTitle('Existing g2 Plot')
                    msgBox.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
                    returnValue = msgBox.exec()
                    if returnValue == QMessageBox.Ok:
                        self.resetg2Plot()
                    else:
                        return
                elif self.modesCombobox.currentText() == 'singles' and self._counts_plotted == True:
                    msgBox = QtWidgets.QMessageBox()
                    msgBox.setIcon(QtWidgets.QMessageBox.Information)
                    msgBox.setText('A Singles plot already exists. Clear the old plot and start anew?')
                    msgBox.setWindowTitle('Existing Singles Plot')
                    msgBox.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
                    returnValue = msgBox.exec()
                    if returnValue == QMessageBox.Ok:
                        self.resetCountsPlot()
                    else:
                        return
                elif self.modesCombobox.currentText() == 'pairs' and self._counts_plotted == True:
                    msgBox = QtWidgets.QMessageBox()
                    msgBox.setIcon(QtWidgets.QMessageBox.Information)
                    msgBox.setText('A Pairs plot already exists. Clear the old plot and start anew?')
                    msgBox.setWindowTitle('Existing Pairs Plot')
                    msgBox.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
                    returnValue = msgBox.exec()
                    if returnValue == QMessageBox.Ok:
                        self.resetCountsPlot()
                    else:
                        return
            self.selectLogfile_Button.setEnabled(False)
            self.modesCombobox.setEnabled(False)
            self.levelsComboBox.setEnabled(False)
            self.devCombobox.setEnabled(False)
            self.runtimeSpinbox.setEnabled(False)
            self.runtime_Checkbox.setEnabled(False)
            if self._dev_mode == 'singles' or self._dev_mode == 'pairs':
                self.enableSinglesOptions()
                self.resetRadioButtons()
            elif self._dev_mode == 'g2':
                self.enableg2Options()
                
            self.liveStart_Button.setText("Live Stop")
            self.liveStart_Button.setProperty("active", True)
            self.liveStart_Button.style().unpolish(self.liveStart_Button)
            self.liveStart_Button.style().polish(self.liveStart_Button)
            
            if self.runtime_Checkbox.isChecked():
                self._runtime = self.runtimeSpinbox.value()*60
                self.startTimer()
            if self._tdc1_dev: self._tdc1_dev._com.reset_input_buffer()
            self.startLogging()

    def startLogging(self):
        self.logger = logWorker()
        self.logger_thread = QtCore.QThread(self) 
        self.logger.moveToThread(self.logger_thread)
        self.logger_thread.start() 
        self.logging_requested.connect(self.logger.log_which_data)
        self.logger.data_is_logged.connect(self.update_counts_plot_from_thread)
        self.logger.histogram_logged.connect(self.updateHistogram)
        self.logger.thread_finished.connect(self.closethreads_ports_timers)
        self.logger.permission_error.connect(self.logfile_permission_error_reset)

        self.logger.int_time = int(self.integrationSpinBox.text()) * 1e-3 
        self.logging_requested.emit(self.integration_time, self._logfile_name, self._dev_path, self.log_flag, self._dev_mode, \
            self._tdc1_dev, self._ch_start, self._ch_stop, self.offset, self.bin_width)
        

    @QtCore.pyqtSlot()
    def selectLogfile(self):
        if self.acq_flag == False:
            if self.selectLogfile_Button.text() == 'Select Logfile':
                default_filetype = 'csv'
                start = datetime.now().strftime("%Y%m%d_%Hh%Mm%Ss ") + "_TDC1." + default_filetype
                self._logfile_name = QtWidgets.QFileDialog.getSaveFileName(
                    self, "Save to log file", start)[0]
                self.logfileText.setText(self._logfile_name)
                if self._logfile_name != '':
                    self.log_flag = True
                    self.selectLogfile_Button.setText('Unselect Logfile')
            elif self.selectLogfile_Button.text() == 'Unselect Logfile':
                self.logfileText.setText('')
                self._logfile_name = ''
                self.log_flag = False
                self.selectLogfile_Button.setText('Select Logfile')

    @QtCore.pyqtSlot(float, float, tuple, str, list)
    def update_counts_plot_from_thread(self, start: float, now: float, data: tuple, dev_mode: str, radio_flags: list):
        next_time = now-start
        
        # Determine what data to plot based on dev_mode
        # 'singles' -> plot data[0:4] (Singles)
        # 'pairs'   -> plot data[4:8] (Coincidences)
        plot_data = []
        if dev_mode == 'singles':
            plot_data = [data[0], data[1], data[2], data[3]]
        elif dev_mode == 'pairs':
            plot_data = [data[4], data[5], data[6], data[7]]
        else:
            plot_data = [0, 0, 0, 0] # Fallback

        if len(self.x) == PLT_SAMPLES:
            self.x = self.x[1:]
            self.x.append(next_time)
            self.y1 = self.y1[1:]; self.y2 = self.y2[1:]; self.y3 = self.y3[1:]; self.y4 = self.y4[1:]
            self.y1.append(plot_data[0]); self.y2.append(plot_data[1]); self.y3.append(plot_data[2]); self.y4.append(plot_data[3])
            self.y_data = [self.y1, self.y2, self.y3, self.y4]
        elif len(self.x) < self.plotSamples:
            self.x.append(next_time)
            self.y1.append(plot_data[0]); self.y2.append(plot_data[1]); self.y3.append(plot_data[2]); self.y4.append(plot_data[3])
            self.idx = min(len(self.y1), self.plotSamples)
            self.y1 = self.y1[-self.idx:]; self.y2 = self.y2[-self.idx:]; self.y3 = self.y3[-self.idx:]; self.y4 = self.y4[-self.idx:]
            self.y_data = [self.y1, self.y2, self.y3, self.y4]
            self._radio_flags = radio_flags
        elif len(self.x) > self.plotSamples:
            cutoff_idx = self.plotSamples + 1
            self.x = self.x[-cutoff_idx:]
            self.x.append(next_time)
            self.y1 = self.y1[-cutoff_idx:]; self.y2 = self.y2[-cutoff_idx:]; self.y3 = self.y3[-cutoff_idx:]; self.y4 = self.y4[-cutoff_idx:]
            self.y1.append(plot_data[0]); self.y2.append(plot_data[1]); self.y3.append(plot_data[2]); self.y4.append(plot_data[3])
            self.y_data = [self.y1, self.y2, self.y3, self.y4]
            
        if dev_mode == 'singles':
            self.Ch1CountsLabel.setText(str(data[0]))
            self.Ch2CountsLabel.setText(str(data[1]))
            self.Ch3CountsLabel.setText(str(data[2]))
            self.Ch4CountsLabel.setText(str(data[3]))
            self.lbl_mon_1.setText(str(data[0]))
            self.lbl_mon_2.setText(str(data[1]))
            self.lbl_mon_3.setText(str(data[2]))
            self.lbl_mon_4.setText(str(data[3]))
        elif dev_mode == 'pairs':
            self.Ch1CountsLabel.setText(str(data[4]))
            self.Ch2CountsLabel.setText(str(data[5]))
            self.Ch3CountsLabel.setText(str(data[6]))
            self.Ch4CountsLabel.setText(str(data[7]))
            self.lbl_mon_1.setText(str(data[4]))
            self.lbl_mon_2.setText(str(data[5]))
            self.lbl_mon_3.setText(str(data[6]))
            self.lbl_mon_4.setText(str(data[7]))

        self._counts_plotted = True
        self._data_plotted = self._counts_plotted or self._g2_plotted
        self.updatePlots(self._radio_flags)
    
    def updatePlots(self, radio_flags: list):
        for i in range(len(radio_flags)):
            if radio_flags[i] == 1:
                self.linePlots[i].setData(self.x[-self.idx:], self.y_data[i][-self.idx:])

    @QtCore.pyqtSlot('PyQt_PyObject')
    def displayPlot1(self, b: QRadioButton):
        if b.isChecked() == True:
            self._radio_flags[0] = 1
            self.updatePlots(self._radio_flags)
            self.linePlot1.setPen(self.lineStyle1)
            if self.logger:
                self.logger.radio_flags[0] = 1
        elif b.isChecked() == False:
            self._radio_flags[0] = 0
            self.linePlot1.setPen(None)
            if self.logger:
                self.logger.radio_flags[0] = 0
                
    @QtCore.pyqtSlot('PyQt_PyObject')
    def displayPlot2(self, b: QRadioButton):
        if b.isChecked() == True:
            self._radio_flags[1] = 1
            self.updatePlots(self._radio_flags)
            self.linePlot2.setPen(self.lineStyle2)
            if self.logger:
                self.logger.radio_flags[1] = 1  
        elif b.isChecked() == False:
            self._radio_flags[1] = 0
            self.linePlot2.setPen(None)
            if self.logger:
                self.logger.radio_flags[1] = 0

    @QtCore.pyqtSlot('PyQt_PyObject')
    def displayPlot3(self, b: QRadioButton):
        if b.isChecked() == True:
            self._radio_flags[2] = 1
            self.updatePlots(self._radio_flags)
            self.linePlot3.setPen(self.lineStyle3)
            if self.logger:
                self.logger.radio_flags[2] = 1
        elif b.isChecked() == False:
            self._radio_flags[2] = 0
            self.linePlot3.setPen(None)
            if self.logger:
                self.logger.radio_flags[2] = 0

    @QtCore.pyqtSlot('PyQt_PyObject')
    def displayPlot4(self, b: QRadioButton):
        if b.isChecked() == True:
            self._radio_flags[3] = 1
            self.updatePlots(self._radio_flags)
            self.linePlot4.setPen(self.lineStyle4)
            if self.logger:
                self.logger.radio_flags[3] = 1
        elif b.isChecked() == False:
            self._radio_flags[3] = 0
            self.linePlot4.setPen(None)
            if self.logger:
                self.logger.radio_flags[3] = 0

    @QtCore.pyqtSlot(str)
    def updateStart(self, channel: str):
        cs = int(channel)
        self._ch_start = cs
        if self.acq_flag == True and self.modesCombobox.currentText() == "g2":
            if self.logger:
                self.logger.ch_start = cs

    @QtCore.pyqtSlot(str)
    def updateStop(self, channel: str):
        cs = int(channel)
        self._ch_stop = cs
        if self.acq_flag == True and self.modesCombobox.currentText() == "g2":
            if self.logger:
                self.logger.ch_stop = cs

    @QtCore.pyqtSlot(str)
    def updateLevel(self, level: str):
        if level == 'TTL (+1.6V)' and self._tdc1_dev:
            print('entering TTL block')
            self._level = 'TTL'
            self._tdc1_dev.level = 'TTL'
            print(f'Device at {self._dev_path} is now at {self._level} level')
        elif level == 'NIM (-0.5V)' and self._tdc1_dev:
            print('entering NIM block')
            self._level = 'NIM'
            self._tdc1_dev.level = 'NIM'
            print(f'Device at {self._dev_path} is now at {self._level} level')
        elif level == 'Select':
            pass

    @QtCore.pyqtSlot(dict, int, int)
    def updateHistogram(self, g2_data: dict, bins: int, bin_width: int):
        incremental_y = g2_data['histogram']
        incremental_y_int = incremental_y.astype(np.int32)
        beans = len(incremental_y_int)
        self.y0 = self.wonkyAdd(y0 = self.y0, incremental = incremental_y_int)
        self.x0 = np.arange(0, beans*bin_width, bin_width)
        self.histogramPlot.setData(self.x0, self.y0)
        totalpairs = np.sum(self.y0, dtype=np.int32)
        self._g2_plotted = True
        self._data_plotted = self._counts_plotted or self._g2_plotted
        self.g2RateLabel.setText("Total Pairs: " + str(totalpairs))
    
    @staticmethod
    def wonkyAdd(y0: np.array, incremental: np.array):
        if len(y0) == len(incremental):
            y0 += incremental
        elif len(y0) < len(incremental):
            diff = len(incremental) - len(y0)
            pad = np.zeros(diff, dtype = np.int32)
            y0 = np.append(y0, pad)
            y0 += incremental
        elif len(y0) > len(incremental):
            y0 = y0[:len(incremental)]
            y0 += incremental
        return y0

    @QtCore.pyqtSlot(int)
    def updateBinwidth(self, bin_width):
        self.binsize = bin_width
        self.bin_width = bin_width
        if self.logger:
            self.logger.bin_width = bin_width
        self.x0 = np.arange(0, self.bins*self.binsize, bin_width) 

    @QtCore.pyqtSlot(int)
    def updateRuntime(self, runtime):
        runtime_mins = runtime*60
        self._runtime = runtime_mins
        if self.logger:
            self.logger.runtime = runtime_mins

    def endRun(self):
        self.liveStart_Button.setEnabled(False)
        QtCore.QTimer.singleShot(1000, lambda: self.liveStart_Button.setEnabled(True)) 
        self.acq_flag = False
        self.log_flag = False
        if self.logger:
            self.logger.active_flag = False
        self.stopWorkerAndThread()
        self.stopTimer()
        self.selectLogfile_Button.setEnabled(True)
        self.liveStart_Button.setText("Live Start")
        self.liveStart_Button.setProperty("active", False)
        self.liveStart_Button.style().unpolish(self.liveStart_Button)
        self.liveStart_Button.style().polish(self.liveStart_Button)

    def startTimer(self):
        time = self.timer.start(1000)
        self.timer.timeout.connect(self.updateTimer)
    
    def stopTimer(self):
        if self.timer.isActive():
            self.timer.stop()
            try:
                self.timer.timeout.disconnect()
            except:
                pass

    def updateTimer(self):
        if self._runtime > 0:
            self.countdownLabel.setStyleSheet("color: white; font-size: 24px; font-family: monospace; font-weight: bold;")
            self._runtime -= 1
            total_seconds = self._runtime
            hours = total_seconds // 3600
            total_seconds = total_seconds - (hours * 3600)
            minutes = total_seconds // 60
            seconds = total_seconds - (minutes * 60)
            self.countdownLabel.setText("{:02}:{:02}:{:02}".format(int(hours), int(minutes), int(seconds)))
        else:
            self.countdownLabel.setStyleSheet("color: gray; font-size: 24px; font-family: monospace;")
            print(f'Timer is up! Data was collected for {self.runtimeSpinbox.value()} minute(s).')
            self.endRun()

    def StrongResetInternalVariables(self):
        self.integration_time = 1
        self._logfile_name = '' 
        self.log_flag = False
        self.deleteWorkerAndThread()
        try:
            if self._tdc1_dev: self._tdc1_dev._com.close()
        except AttributeError:
            print('TDC1 object not yet created.')
        finally:
            self._tdc1_dev = None 
            self._dev_mode = ''
            self._dev_path = '' 

    def WeakResetInternalVariables(self):
        self.integration_time = 1
        self._logfile_name = '' 
        self.log_flag = False
        self.deleteWorkerAndThread()

    def stopWorkerAndThread(self):
        QtCore.QTimer.singleShot(1000, self.dummy)
        if self.logger_thread:
            if self.logger:
                self.logger.active_flag = False
                self.logger_thread.quit()
                self.logger_thread.wait()

    def deleteWorkerAndThread(self):
        self.stopWorkerAndThread()
        self.logger = None
        self.logger_thread = None

    def enableDevOptions(self):
        self.modesCombobox.setEnabled(True)
        self.levelsComboBox.setEnabled(True)
        self.integrationSpinBox.setEnabled(True)
        self.samplesSpinbox.setEnabled(True)
        self.liveStart_Button.setEnabled(True)
        self.selectLogfile_Button.setEnabled(True)
        self.runtimeSpinbox.setEnabled(True)

    def disableDevOptions(self):
        self.modesCombobox.setEnabled(False)
        self.levelsComboBox.setEnabled(False)
        self.integrationSpinBox.setEnabled(False)
        self.samplesSpinbox.setEnabled(False)
        self.liveStart_Button.setEnabled(False)
        self.selectLogfile_Button.setEnabled(False)

    def enableSinglesOptions(self):
        self.radio1_Button.setEnabled(True)
        self.radio2_Button.setEnabled(True)
        self.radio3_Button.setEnabled(True)
        self.radio4_Button.setEnabled(True)

    def disableSinglesOptions(self):
        self.radio1_Button.setEnabled(False)
        self.radio2_Button.setEnabled(False)
        self.radio3_Button.setEnabled(False)
        self.radio4_Button.setEnabled(False)

    def enableg2Options(self):
        self.channelsCombobox1.setEnabled(True)
        self.channelsCombobox2.setEnabled(True)
        self.offsetSpinbox.setEnabled(True)
        self.resolutionSpinbox.setEnabled(True)

    def disableg2Options(self):
        self.channelsCombobox1.setEnabled(False)
        self.channelsCombobox2.setEnabled(False)
        self.offsetSpinbox.setEnabled(False)
        self.resolutionSpinbox.setEnabled(False)
    
    def resetGUIelements(self):
        self.liveStart_Button.setEnabled(True)
        self.selectLogfile_Button.setEnabled(True)
        self.logfileText.setText('')
        self.selectLogfile_Button.setText('Select Logfile')
        self.resetRadioButtons()
        self.integrationSpinBox.setValue(1000)
        self.samplesSpinbox.setValue(501)
        self.runtimeSpinbox.setValue(5)
        self.modesCombobox.setCurrentText('Select mode')

    def resetRadioButtons(self):
        self.radio1_Button.setChecked(False)
        self.radio2_Button.setChecked(False)
        self.radio3_Button.setChecked(False)
        self.radio4_Button.setChecked(False)

    def resetCountsPlot(self):
        self.x=[]
        self.y1=[]
        self.y2=[]
        self.y3=[]
        self.y4=[]
        self.linePlot1.setData(self.x, self.y1)
        self.linePlot2.setData(self.x, self.y2)
        self.linePlot3.setData(self.x, self.y3)
        self.linePlot4.setData(self.x, self.y4)
        self.resetRadioButtons()
        self._counts_plotted = False
        self._data_plotted = self._counts_plotted or self._g2_plotted

    def resetg2Plot(self):
        self.x0=np.arange(0, self.bins*self.binsize, self.binsize)
        self.y0=np.zeros_like(self.x0)
        self.histogramPlot.setData(self.x0, self.y0)
        self._radio_flags = [0,0,0,0]
        self._g2_plotted = False
        self._data_plotted = self._counts_plotted or self._g2_plotted

    def resetDataAndPlots(self):
        self.resetCountsPlot()
        self.resetg2Plot()

    @QtCore.pyqtSlot()
    def clearCountsDataData(self):
        msgBox = QtWidgets.QMessageBox()
        msgBox.setIcon(QtWidgets.QMessageBox.Information)
        msgBox.setText('Any Counts data unsaved to logfile will be lost. Click Ok to confirm.')
        msgBox.setWindowTitle('Confirm Clear Singles.')
        msgBox.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        returnValue = msgBox.exec()
        if returnValue == QMessageBox.Ok:
            self.resetCountsPlot()

    @QtCore.pyqtSlot()
    def clearg2DataData(self):
        msgBox = QtWidgets.QMessageBox()
        msgBox.setIcon(QtWidgets.QMessageBox.Information)
        msgBox.setText('Any g2 data unsaved to logfile will be lost. Click Ok to confirm.')
        msgBox.setWindowTitle('Confirm Clear Pairs.')
        msgBox.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        returnValue = msgBox.exec()
        if returnValue == QMessageBox.Ok:
            self.resetg2Plot()
    
    @QtCore.pyqtSlot()
    def dummy(self):
        pass

    def cleanUp(self):
        print('Performing cleanup...')
        self.acq_flag = False
        self.log_flag = False
        if self.logger:
            self.logger.active_flag = False
        self.stopWorkerAndThread()
        self.stopTimer()
        print('Exiting app, bye!')

def main():
        app = QApplication(sys.argv)
        # High DPI Scaling Fixes
        app.setAttribute(Qt.AA_EnableHighDpiScaling)
        app.setAttribute(Qt.AA_UseHighDpiPixmaps)
        
        win = MainWindow()
        win.show()
        app.aboutToQuit.connect(win.cleanUp)
        sys.exit(app.exec_())
    
if __name__ == '__main__':
    main()