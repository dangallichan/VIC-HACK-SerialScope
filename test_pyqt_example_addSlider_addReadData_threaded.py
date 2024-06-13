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

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import Qt

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar


# from matplotlib.figure import Figure
from matplotlib import pyplot as plt

SER_TIMEOUT = 2                   # Timeout for serial Rx
baudrate    = 115200                # Default baud rate
portname    = "COM12"                # Default port name
N_CHANNELS = 4


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)


        layout = QtWidgets.QVBoxLayout()

        self.setMinimumSize(800, 600)
        
        # create plot and put into layout
        self.fig, self.ax1 = plt.subplots(figsize=(8,5))
        self.plotWidget = FigureCanvas(self.fig)
        layout.addWidget(self.plotWidget)

        self.n_xpts = 50
        self.n_channels = N_CHANNELS

        self.useRandomData = False
        #if self.useRandomData:
        #    self.xdata = np.linspace(1, self.n_xpts, self.n_xpts)
        #    self.ydata = np.random.randint(10, size=(self.n_xpts, self.n_channels))
        #else:
        # self.xdata = np.zeros((1, 1),dtype=float)
        # self.ydata = np.zeros((1, self.n_channels),dtype=float)
        self.xdata = np.linspace(1, self.n_xpts, self.n_xpts)
        self.ydata = np.random.randint(10, size=(self.n_xpts, self.n_channels))
        
        self.Yoffset = 0.0

        # self.color = iter(plt.cm.rainbow(np.linspace(0, 1, self.n_channels)))
        self.color = iter(plt.cm.Set1(np.linspace(0, 1, self.n_channels)))

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
        self.slYOffset.valueChanged.connect(self.valuechange)

        layout.addWidget(self.slYGlobalScale)
        self.slYGlobalScale.valueChanged.connect(self.valuechange)

        # We need to store a reference to the plotted line
        # somewhere, so we can apply the new data to it.
        self._plot_refs = [None] * self.n_channels
        # self._plot_refs = None
        for iPlot in range(self.n_channels):
                self._plot_refs[iPlot] = self.ax1.plot(self.xdata, self.ydata[:,iPlot] + self.Yoffset*iPlot, color=next(self.color))[0]
        # self.update_plot()
        self.ax1.set_ylim(0, 50)

        # print(self._plot_refs[0])

        self.serth = SerialThread(portname, baudrate)   # Start serial reading thread
        self.serth.start()

        self.serth.signalData.connect(self.addNewData)



        # Setup a timer to trigger the redraw by calling update_plot.
        self.timer = QtCore.QTimer()
        self.timer.setInterval(50)
        self.timer.timeout.connect(self.update_plot)
        self.timer.start()

        # central widget for QMainWindow
        centralWidget = QtWidgets.QWidget()
        centralWidget.setLayout(layout)
        self.setCentralWidget(centralWidget)
        self.setWindowTitle("WaveMage v0.1")

        self.show()

    def addNewData(self, y):
        # print('received data')
        # self.ydata = np.vstack((self.ydata,y))
        self.ydata = np.roll(self.ydata, -1, axis=0)
        self.ydata[-1,:] = y

    def valuechange(self):
        # obtain value from slider
        # self.ax1.set_ylim(self.n_channels*self.slOffset.value())
        self.Yoffset = self.slYOffset.value()
        self.YGlobalScale = self.slYGlobalScale.value() / self.GlobalScaleFactor

    def update_plot(self):
        # Drop off the first y element, append a new one.
        # self.ydata = np.roll(self.ydata, -1, axis=0)
        if self.useRandomData:
            self.ydata[-1,:] = np.random.randint(10, size=(1, self.n_channels))
        else:
            pass
            # self.read_data()

       
        # We have a reference, we can use it to update the data for that line.
        for iPlot in range(self.n_channels):
            #print(self.ydata[:,iPlot])
            self._plot_refs[iPlot].set_ydata(self.YGlobalScale * self.ydata[:,iPlot] + self.Yoffset*iPlot)

        # Trigger the canvas to update and redraw.
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()
        
    # def read_data(self):
    #     # ser = serial.Serial('/dev/ttyACM0', baudrate=115200)
    #     ser = serial.Serial('COM12', baudrate=115200)
    #     try:
    #         y = np.array([yy.split(",") for yy in ser.readline().decode("utf-8").split()][0],dtype=float)
    #         if len(y) == self.n_channels:
    #             self.ydata[-1,:] = y
        
    #     except:
    #         pass
    #     #self.ydata[-1,:] = np.vstack((self.ydata,y))  # uncomment to save all data


# Thread to handle incoming & outgoing serial data
class SerialThread(QtCore.QThread):

    signalData = QtCore.pyqtSignal(np.ndarray)  # Signal to send data to main thread

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
            # print('reading')
            # s = self.ser.readline()
            # print(s)
            try:
                y = np.array([yy.split(",") for yy in self.ser.readline().decode("utf-8").split()][0],dtype=float)
                # print(y)
                if len(y) == N_CHANNELS:
                    self.signalData.emit(y)
                    # if random.random() > 0.9:
                    #     print(y)    
                    # print(self.ydata[-1,:])
            except:
                pass

        if self.ser:                                    # Close serial port when thread finished
            self.ser.close()
            self.ser = None


app = QtWidgets.QApplication(sys.argv)
w = MainWindow()
app.exec()