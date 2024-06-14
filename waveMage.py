#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jun 13 15:11:38 2024

@author: epowell
"""
import serial
import numpy as np
import sys
import random
import matplotlib 
matplotlib.use('QtAgg')
import time

try:
    import Queue
except:
    import queue as Queue

import numpy as np

from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtCore import Qt

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar


# from matplotlib.figure import Figure
from matplotlib import pyplot as plt

SER_TIMEOUT = 2                   # Timeout for serial Rx
baudrate    = 115200              # Default baud rate
# portname    = "/dev/ttyACM1"      # Default port name
portname = "COM12"
MAX_N_DATA_CHANNELS = 12
WINDOW_TITLE = "WaveMage v0.1"


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)


        layout = QtWidgets.QVBoxLayout()

        self.setMinimumSize(800, 600)
        
        self.n_data_channels = 3
        self.firstChannelIsTime = True


        # create plot and put into layout
        self.fig, self.ax1 = plt.subplots(self.n_data_channels,figsize=(8,5))
        self.plotWidget = FigureCanvas(self.fig)
        layout.addWidget(self.plotWidget)

        self.n_xpts = 200

        self.useRandomData = False
        #if self.useRandomData:
        #    self.xdata = np.linspace(1, self.n_xpts, self.n_xpts)
        #    self.ydata = np.random.randint(10, size=(self.n_xpts, self.n_data_channels))
        #else:
        # self.xdata = np.zeros((1, 1),dtype=float)
        # self.ydata = np.zeros((1, self.n_data_channels),dtype=float)
        self.xdata = np.linspace(1, self.n_xpts, self.n_xpts)
        # self.ydata = np.random.randint(10, size=(self.n_xpts, self.n_data_channels))
        self.ydata = np.zeros((self.n_xpts, self.n_data_channels + int(self.firstChannelIsTime)),dtype=float)


        self.Yoffset = 0.0

        # self.color = iter(plt.cm.rainbow(np.linspace(0, 1, self.n_data_channels)))
        self.color = iter(plt.cm.Set1(np.linspace(0, 1, self.n_data_channels)))

        # add toolbar
        self.addToolBar(Qt.BottomToolBarArea, NavigationToolbar(self.plotWidget, self))
        
        # slider for y-axis offset
        self.slYOffset = QtWidgets.QSlider(Qt.Horizontal)
        self.slYOffset.setMinimum(0)
        self.slYOffset.setMaximum(40)
        self.slYOffset.setValue(1)
        self.slYOffset.setTickPosition(QtWidgets.QSlider.TicksBelow)
        self.slYOffset.setTickInterval(1)

        # slider for y-scaling
        self.slYGlobalScale = QtWidgets.QSlider(Qt.Horizontal)
        self.slYGlobalScale.setMinimum(0)
        self.slYGlobalScale.setMaximum(100)
        self.slYGlobalScale.setValue(10)
        self.slYGlobalScale.setTickPosition(QtWidgets.QSlider.TicksBelow)
        self.slYGlobalScale.setTickInterval(1)
        self.GlobalScaleFactor = 1000.0
        self.YGlobalScale = self.slYGlobalScale.value() / self.GlobalScaleFactor

        
        # update along with slider movement
        layout.addWidget(self.slYOffset)
        self.slYOffset.valueChanged.connect(self.updateGUI)

        layout.addWidget(self.slYGlobalScale)
        self.slYGlobalScale.valueChanged.connect(self.updateGUI)

        # We need to store a reference to the plotted line
        # somewhere, so we can apply the new data to it.
        self._plot_refs = [None] * MAX_N_DATA_CHANNELS
        for iPlot in range(self.n_data_channels):
                self._plot_refs[iPlot] = self.ax1[iPlot].plot(self.xdata, self.ydata[:,iPlot + int(self.firstChannelIsTime)], color=next(self.color))[0]
                self.ax1[iPlot].set_ylabel('Channel ' + str(iPlot + 1))

        self.serth = SerialThread(portname, baudrate)   # Start serial reading thread
        self.serth.start()

        self.serth.signalDataAsMatrix.connect(self.addNewData)


        # have somewhere to display the serial data as text
        self.serialDataView = SerialDataView(self)
        layout.addWidget(self.serialDataView)
        self.serialDataView.serialData.append("Serial Data:\n")
        self.serth.signalDataAsString.connect(self.serialDataView.appendSerialText)


        # Setup a timer to trigger the redraw by calling plotData.
        self.timer = QtCore.QTimer()
        self.timer.setInterval(50)
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
        #self.ydata = np.vstack((self.ydata,y))
        self.ydata = np.roll(self.ydata, -1, axis=0)
        self.ydata[-1,:] = y

    def updateGUI(self):
        # obtain value from slider
        # self.ax1.set_ylim(self.n_data_channels*self.slOffset.value())
        self.Yoffset = self.slYOffset.value()
        self.YGlobalScale = self.slYGlobalScale.Queuevalue() / self.GlobalScaleFactor

    def plotData(self):
        # Drop off the first y element, append a new one.
        # self.ydata = np.roll(self.ydata, -1, axis=0)
        if self.useRandomData:
            self.ydata[-1,:] = np.random.randint(10, size=(1, self.n_data_channels))
        else:
            pass
            # self.read_data()

       
        # We have a reference, we can use it to update the data for that line.
        for iPlot in range(self.n_data_channels):
            #print(self.ydata[:,iPlot])
            # self._plot_refs[iPlot].set_ydata(self.YGlobalScale * self.ydata[:,iPlot] + self.Yoffset*iPlot)
            self._plot_refs[iPlot].set_ydata(self.ydata[:,iPlot + int(self.firstChannelIsTime)])
            if np.any(self.ydata[:,iPlot + int(self.firstChannelIsTime)]):
                self.ax1[iPlot].set_ylim(min(self.ydata[:,iPlot + int(self.firstChannelIsTime)]), max(self.ydata[:,iPlot + int(self.firstChannelIsTime)]))
            else:
                self.ax1[iPlot].set_ylim(-1, 1)

        # Trigger the canvas to update and redraw.
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()
        

# Thread to handle incoming & outgoing serial data
class SerialThread(QtCore.QThread):

    signalDataAsMatrix = QtCore.pyqtSignal(np.ndarray)  # Signal to send data to main thread
    signalDataAsString = QtCore.pyqtSignal(str)        

    def __init__(self, portname, baudrate): # Initialise with serial port details
        QtCore.QThread.__init__(self)
        self.portname, self.baudrate = portname, baudrate
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
                if len(y) == 4:   ## HARD-CODED - NEEDS FIXING!
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
        self.serialData.setMinimumSize(200, 200)
        # self.serialData.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        
    def appendSerialText(self, appendText):
        self.serialData.moveCursor(QtGui.QTextCursor.End)
        self.serialData.setFontFamily('Courier New')
        
        self.serialData.insertPlainText(appendText)
        
        self.serialData.moveCursor(QtGui.QTextCursor.End)

app = QtWidgets.QApplication(sys.argv)
w = MainWindow()
app.exec()