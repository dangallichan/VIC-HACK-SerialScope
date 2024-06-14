#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jun 13 15:11:38 2024

@author: epowell
"""
import serial
import serial.tools.list_ports
import numpy as np
import sys
import random
import matplotlib 
matplotlib.use('QtAgg')
import time
from datetime import datetime
import os

try:
    import Queue
except:
    import queue as Queue

import numpy as np

from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtCore import Qt

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

# from matplotlib.figure import Figure
from matplotlib import pyplot as plt

SER_TIMEOUT = 2                   # Timeout for serial Rx
baudrate    = 115200              # Default baud rate
MAX_N_DATA_CHANNELS = 12
WINDOW_TITLE = "WaveMage v0.1"
MINWIDTH, MINHEIGHT = 800, 800
MAX_X_DATA_RANGE = 10000

os.chdir(os.path.dirname(os.path.abspath(__file__)))

def getSerialPort():
    ports = serial.tools.list_ports.comports(include_links=False)
    for port in ports :
        print('Find port '+ port.device)
    
    if len(ports) == 0:
        print('No serial port found')
        return None

    return port.device

    # To manually override the port selection do something like this:
    # return "COM11"
    # return "/dev/ttyUSB0"
    # return "/dev/ttyACM0"


# # Get 10 lines of data at start to check our data stream
# ser = serial.Serial(getSerialPort(), baudrate, timeout=SER_TIMEOUT)
# time.sleep(SER_TIMEOUT*1.2)
# ser.flushInput()
# for i in range(10):
#     print(ser.readline().decode("utf-8"))
# ser.close()

class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, *args, **kwargs):
        
        portname = getSerialPort()
        print(portname)
        
        super(MainWindow, self).__init__(*args, **kwargs)


        layout = QtWidgets.QVBoxLayout()

        self.setMinimumSize(MINWIDTH, MINHEIGHT)
        
        self.n_data_channels = 3
        self.xScaleFactor = 1e-6
        self.firstChannelIsTime = True


        # create plot and put into layout
        self.fig, self.ax1 = plt.subplots(self.n_data_channels,figsize=(8,5))
        self.plotWidget = FigureCanvas(self.fig)
        layout.addWidget(self.plotWidget)

        self.n_xpts = 50

        # initialize data
        self.xdata = np.linspace(1, self.n_xpts, self.n_xpts)
        self.ydata = np.zeros((self.n_xpts, self.n_data_channels + int(self.firstChannelIsTime)),dtype=float)


        # self.color = iter(plt.cm.rainbow(np.linspace(0, 1, self.n_data_channels)))
        self.color = iter(plt.cm.Set1(np.linspace(0, 1, self.n_data_channels)))

        
        # slider for x-axis range
        self.slXDataRange = QtWidgets.QSlider(Qt.Horizontal)
        self.slXDataRange.setMinimum(5)
        self.slXDataRange.setMaximum(MAX_X_DATA_RANGE)
        self.slXDataRange.setValue(MAX_X_DATA_RANGE-50)
        self.slXDataRange.setTickPosition(QtWidgets.QSlider.TicksBelow)
        self.slXDataRange.setTickInterval(1)

        # update along with slider movement
        layout.addWidget(self.slXDataRange)
        self.slXDataRange.valueChanged.connect(self.updateGUI)

        # We need to store a reference to the plotted line
        # somewhere, so we can apply the new data to it.
        self._plot_refs = [None] * MAX_N_DATA_CHANNELS
        for iPlot in range(self.n_data_channels):
                self._plot_refs[iPlot] = self.ax1[iPlot].plot(self.xdata, self.ydata[-self.n_xpts:,iPlot + int(self.firstChannelIsTime)], color=next(self.color))[0]
                self.ax1[iPlot].set_ylabel('Ch ' + str(iPlot + 1))

        self.serth = SerialThread(portname, baudrate, self.n_data_channels, self.firstChannelIsTime)   # Start serial reading thread
        self.serth.start()

        self.serth.signalDataAsMatrix.connect(self.addNewData)

        self.saveButton = QtWidgets.QPushButton("save those numbers", self)
        layout.addWidget(self.saveButton)
        self.saveButton.clicked.connect(self.saveData)

        # # have somewhere to display the serial data as text
        self.serialDataView = SerialDataView(self)
        layout.addWidget(self.serialDataView)
        self.serialDataView.serialData.append("Serial Data:\n")
        self.serth.signalDataAsString.connect(self.serialDataView.appendSerialText)


        # Setup a timer to trigger the redraw by calling plotData.
        self.timer = QtCore.QTimer()
        self.timer.setInterval(10)
        self.timer.timeout.connect(self.plotData)
        self.timer.start()

        # central widget for QMainWindow
        centralWidget = QtWidgets.QWidget()
        centralWidget.setLayout(layout)
        self.setCentralWidget(centralWidget)
        self.setWindowTitle(WINDOW_TITLE)

        self.show()

    def addNewData(self, y):
        # print('received data')
        self.ydata = np.vstack((self.ydata,y))

    def updateGUI(self):
        self.n_xpts = MAX_X_DATA_RANGE - self.slXDataRange.value()
        self.n_xpts = max(5, self.n_xpts)

    def plotData(self):
    
        # update graphed data for each channel
        for iPlot in range(self.n_data_channels):
            #print(self.ydata[:,iPlot])
            # self._plot_refs[iPlot].set_ydata(self.YGlobalScale * self.ydata[:,iPlot] + self.Yoffset*iPlot)
            if self.firstChannelIsTime:
                self._plot_refs[iPlot].set_xdata(self.ydata[-self.n_xpts:,0] * self.xScaleFactor)
                self.ax1[iPlot].set_xlim(min(self.ydata[-self.n_xpts:,0] * self.xScaleFactor), max(self.ydata[-self.n_xpts:,0] * self.xScaleFactor))
            self._plot_refs[iPlot].set_ydata(self.ydata[-self.n_xpts:,iPlot + int(self.firstChannelIsTime)])
            if np.any(self.ydata[:,iPlot + int(self.firstChannelIsTime)]):
                self.ax1[iPlot].set_ylim(min(self.ydata[:,iPlot + int(self.firstChannelIsTime)]), max(self.ydata[:,iPlot + int(self.firstChannelIsTime)]))
            else:
                self.ax1[iPlot].set_ylim(-1, 1)

        # Trigger the canvas to update and redraw.
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()

    def saveData(self):
       today = datetime.today()
       timeis = today.strftime("%Y%m%d_%H%M%S")
       fname = str(timeis)+"_data.csv"
       np.savetxt(fname, self.ydata, fmt='%1.3f')
       print("saved")
    

        

# Thread to handle incoming & outgoing serial data
class SerialThread(QtCore.QThread):

    signalDataAsMatrix = QtCore.pyqtSignal(np.ndarray)  # Signal to send data to main thread
    signalDataAsString = QtCore.pyqtSignal(str)        

    def __init__(self, portname, baudrate, n_data_channels, firstChannelIsTime): # Initialise with serial port details
        QtCore.QThread.__init__(self)
        self.portname, self.baudrate, self.n_data_channels, self.firstChannelIsTime = portname, baudrate, n_data_channels, firstChannelIsTime
        self.txq = Queue.Queue()
        self.running = True

         
    def run(self):                          # Run serial reader thread
        print("Opening %s at %u baud " % (self.portname, self.baudrate))
        try:
            self.ser = serial.Serial(self.portname, self.baudrate, timeout=SER_TIMEOUT)
            time.sleep(SER_TIMEOUT*1.2)
            self.ser.flushInput()
        except:
            self.ser = None
        if not self.ser:
            print("Can't open port")
            self.running = False
        while self.running:
            try:
                thisLine = self.ser.readline().decode("utf-8")
                # print(thisLine)
                self.signalDataAsString.emit(thisLine)
                y = np.array([yy.split(",") for yy in thisLine.split()][0],dtype=float)
                # print(y)                
                if len(y) == self.n_data_channels + int(self.firstChannelIsTime):  # Check data is correct length
                    self.signalDataAsMatrix.emit(y)

            except:
                pass

        if self.ser:                                    # Close serial port when thread finished
            self.ser.close()
            self.ser = None


class SerialDataView(QtWidgets.QWidget):
    def __init__(self, parent):
        super(SerialDataView, self).__init__(parent)
        self.serialData = QtWidgets.QTextEdit(self)
        self.serialData.setReadOnly(True)
        self.serialData.setFontFamily('Courier New')
        self.serialData.setMinimumSize(MINWIDTH, 400)
        # self.serialData.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        
    def appendSerialText(self, appendText):
        self.serialData.moveCursor(QtGui.QTextCursor.End)
        self.serialData.setFontFamily('Courier New')
        
        self.serialData.insertPlainText(appendText)
        
        self.serialData.moveCursor(QtGui.QTextCursor.End)

app = QtWidgets.QApplication(sys.argv)
w = MainWindow()
app.exec()