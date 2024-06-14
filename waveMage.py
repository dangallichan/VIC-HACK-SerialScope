#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import serial
import serial.tools.list_ports
import numpy as np
import sys, os, time
import random
import matplotlib 
matplotlib.use('QtAgg')
from matplotlib import pyplot as plt
plt.rcParams['axes.grid'] = True  # Show gridlines by default

from datetime import datetime

try:
    import Queue
except:
    import queue as Queue

from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtCore import Qt

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas



SER_TIMEOUT = 2                   # Timeout for serial Rx
baudrate    = 115200              # Default baud rate
WINDOW_TITLE = "WaveMage v0.1"
MINWIDTH, MINHEIGHT = 800, 800    # Minimum window size
MAX_X_DATA_RANGE = 10000          # Maximum number of data points to display on x-axis
PLOT_REFRESH_RATE = 30            # Refresh rate for plotting in ms (not sure how quickly we can get this to go!)

# Set working directory to the directory of this script for saving data
os.chdir(os.path.dirname(os.path.abspath(__file__)))

def getSerialPort():
    ports = serial.tools.list_ports.comports(include_links=False)
    for port in ports :
        print('Find port '+ port.device)
    
    if len(ports) == 0:
        print('No serial port found')
        return None

    return port.device

# Attempt to automatically find the serial port
portname = getSerialPort()
print(portname)

# To manually override the port selection do something like this:
# portname = "COM11"          ## Windows
# portname =  "/dev/ttyUSB0"  ## Linux / OSX
# portname =  "/dev/ttyACM0"  ## Linux / OSX


# Get 10 lines of data at start to check our data stream
# makes some fairly hideous assumptions about the data format, but tries to guess
# the number of data channels and whether the first channel is time
ser = serial.Serial(portname, baudrate, timeout=SER_TIMEOUT)
time.sleep(SER_TIMEOUT*1.2)
ser.flushInput()
testLens = np.zeros(10)
firstVals = np.zeros(10)
print("Attempting to read 10 lines of data to determine data format...")
for i in range(10):
    readSuccess = False
    while not readSuccess:
        try:
            thisLine = ser.readline().decode("utf-8")
            newDataRow = np.array([yy.split(",") for yy in thisLine.split()][0],dtype=float)
            readSuccess = True
        except:
            pass
    print(thisLine + " ****  Nvalues: ", len(newDataRow))
    testLens[i] = len(newDataRow)
    firstVals[i] = newDataRow[0]
ser.close()
n_data_channels = int(np.median(testLens))
diffFirstVals = np.diff(firstVals)
meanDiffFirstVals = np.mean(diffFirstVals)
stderrDiffFirstVals = np.std(diffFirstVals)/meanDiffFirstVals
print("Diff of first values: ", diffFirstVals)
print("Stderr of diff of first values: ", stderrDiffFirstVals)
if stderrDiffFirstVals > 1e-3:
    print("First values are not consistent, assuming first channel is not time")
    firstChannelIsTime = False
else:
    print("First values are consistent, assuming first channel is time")
    firstChannelIsTime = True
    n_data_channels -= 1
print("Number of data channels: ", n_data_channels)


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, *args, **kwargs):
        
        super(MainWindow, self).__init__(*args, **kwargs)

        layout = QtWidgets.QVBoxLayout()

        self.setMinimumSize(MINWIDTH, MINHEIGHT)
        
        self.n_data_channels = n_data_channels
        self.xScaleFactor = 1e-6  # currently assumes first channel is time in microseconds
        self.firstChannelIsTime = firstChannelIsTime

         # create plot and put into layout
        self.fig, self.ax1 = plt.subplots(self.n_data_channels, 1, sharex=True, figsize=(10, 6))
        self.ax1[0].set_title('Serial data from ' + portname + ' at ' + str(baudrate) + ' baud')
        self.plotWidget = FigureCanvas(self.fig)
        layout.addWidget(self.plotWidget)

        self.n_xpts = 50
        self.n_xptsAtStart = self.n_xpts
        self.nPtsAcquired = 0   # keeps track of total number of data points acquired - used also for dealing with first n_xpts data points

        # initialize data, xdata as integer counter, ydata as zeros
        self.xdata = np.linspace(1, self.n_xpts, self.n_xpts)
        self.allData = np.zeros((self.n_xpts, self.n_data_channels + int(self.firstChannelIsTime)),dtype=float)

        # color iterator for plotting
        self.color = iter(plt.cm.Set1(np.linspace(0, 1, self.n_data_channels)))
        
        # slider for x-axis range
        self.slXDataRange = QtWidgets.QSlider(Qt.Horizontal)
        self.slXDataRange.setMinimum(5)
        self.slXDataRange.setMaximum(MAX_X_DATA_RANGE)
        self.slXDataRange.setValue(MAX_X_DATA_RANGE-50)
        self.slXDataRange.setTickPosition(QtWidgets.QSlider.TicksBelow)
        self.slXDataRange.setTickInterval(5)
        self.slXDataRange.setSingleStep(5)
        self.slXDataRange.setPageStep(5)

        # update along with slider movement
        layout.addWidget(self.slXDataRange)
        self.slXDataRange.valueChanged.connect(self.updateGUI)

        # create a reference for each channel plot
        self._plot_refs = [None] * self.n_data_channels
        for iPlot in range(self.n_data_channels):
                self._plot_refs[iPlot] = self.ax1[iPlot].plot(self.xdata, self.allData[-self.n_xpts:,iPlot + int(self.firstChannelIsTime)], color=next(self.color))[0]
                self.ax1[iPlot].set_ylabel('Ch ' + str(iPlot + 1))

        self.serialThread = SerialThread(portname, baudrate, self.n_data_channels, self.firstChannelIsTime)   # Start serial reading thread
        self.serialThread.start()

        self.serialThread.signalDataAsMatrix.connect(self.addNewData)

        # save data button
        self.saveButton = QtWidgets.QPushButton("Save data as CSV", self)
        self.saveButton.setMaximumWidth(200)
        layout.addWidget(self.saveButton)
        self.saveButton.clicked.connect(self.saveData)

        # button to toggle the serial data view
        self.toggleSerialDataViewButton = QtWidgets.QPushButton("Toggle Live Serial Data View", self)
        self.toggleSerialDataViewButton.setMaximumWidth(200)
        layout.addWidget(self.toggleSerialDataViewButton)
        self.toggleSerialDataViewButton.setCheckable(True)
        self.toggleSerialDataViewButton.setChecked(True)

        # have somewhere to display the serial data as text
        # For the streaming rates we are using it seems we can get away with just using a text box and continuously appending to it.
        self.serialDataView = SerialDataView(self)
        layout.addWidget(self.serialDataView)
        self.serialThread.signalDataAsString.connect(self.serialDataView.appendSerialText)
        self.toggleSerialDataViewButton.clicked.connect(self.serialDataView.setVisible)
        self.toggleSerialDataViewButton.clicked.connect(self.serialDataView.setReceiveData)


        # Setup a timer to trigger the redraw by calling plotData.
        self.timer = QtCore.QTimer()
        self.timer.setInterval(PLOT_REFRESH_RATE)
        self.timer.timeout.connect(self.plotData)
        self.timer.start()

        # central widget for QMainWindow
        # this is the widget that will contain all our other widgets
        centralWidget = QtWidgets.QWidget()
        centralWidget.setLayout(layout)
        self.setCentralWidget(centralWidget)
        self.setWindowTitle(WINDOW_TITLE)

        self.show()

    def addNewData(self, newDataRow):
        # this function is called when new data is received from the serial port
        # newDataRow is a numpy array of the new data, emitted by the serial thread

        if self.nPtsAcquired == 0:
            self.timeAtStart = newDataRow[0]

        if self.nPtsAcquired < self.n_xptsAtStart:
            self.allData[self.nPtsAcquired,:] = newDataRow
        else:
            self.allData = np.vstack((self.allData,newDataRow)) 
            if not self.firstChannelIsTime:
                self.xdata = np.linspace(1, self.allData.shape[0], self.allData.shape[0])

        self.nPtsAcquired += 1        

    def updateGUI(self):
        # update the GUI based on the slider position
        self.n_xpts = MAX_X_DATA_RANGE - self.slXDataRange.value()
        self.n_xpts = max(5, self.n_xpts)

    def plotData(self):
        # update graphed data for each channel
        for iPlot in range(self.n_data_channels):
            if self.firstChannelIsTime:
                self._plot_refs[iPlot].set_xdata(self.allData[-self.n_xpts:,0] * self.xScaleFactor)
                self.ax1[iPlot].set_xlim(min(self.allData[-self.n_xpts:,0] * self.xScaleFactor), max(self.allData[-self.n_xpts:,0] * self.xScaleFactor))
            else:
                self._plot_refs[iPlot].set_xdata(self.xdata[-self.n_xpts:])
                self.ax1[iPlot].set_xlim(self.nPtsAcquired-self.n_xpts, self.nPtsAcquired)
            
            self._plot_refs[iPlot].set_ydata(self.allData[-self.n_xpts:,iPlot + int(self.firstChannelIsTime)])

            if np.any(self.allData[:,iPlot + int(self.firstChannelIsTime)]):
                self.ax1[iPlot].set_ylim(min(self.allData[:,iPlot + int(self.firstChannelIsTime)]), max(self.allData[:,iPlot + int(self.firstChannelIsTime)]))
            else:  # handle the case that all data is zero
                self.ax1[iPlot].set_ylim(-1, 1)

        # Trigger the canvas to update and redraw.
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()

    def saveData(self):
       # saves the data to a CSV file
       today = datetime.today()
       timeis = today.strftime("%Y%m%d_%H%M%S")
       fname = str(timeis)+"_data.csv"
       np.savetxt(fname, self.allData, fmt='%1.3f')
       print("saved")
    

        

# Thread to handle incoming & outgoing serial data
class SerialThread(QtCore.QThread):

    signalDataAsMatrix = QtCore.pyqtSignal(np.ndarray)  # Signal to send data to main thread
    signalDataAsString = QtCore.pyqtSignal(str)         # Signal to send data to main thread as string

    def __init__(self, portname, baudrate, n_data_channels, firstChannelIsTime): # Initialise with serial port details
        QtCore.QThread.__init__(self)
        self.portname, self.baudrate, self.n_data_channels, self.firstChannelIsTime = portname, baudrate, n_data_channels, firstChannelIsTime
        self.txq = Queue.Queue()
        self.running = True

         
    def run(self):                          
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
                newDataRow = np.array([yy.split(",") for yy in thisLine.split()][0],dtype=float)
                # print(newDataRow)                
                if len(newDataRow) == self.n_data_channels + int(self.firstChannelIsTime):  # Check data is correct length
                    self.signalDataAsMatrix.emit(newDataRow)

            except:
                pass

        if self.ser:                                    # Close serial port when thread finished
            self.ser.close()
            self.ser = None


# Class to display serial data as text
class SerialDataView(QtWidgets.QWidget):
    def __init__(self, parent):
        super(SerialDataView, self).__init__(parent)
        self.serialData = QtWidgets.QTextEdit(self)
        self.serialData.setReadOnly(True)
        self.serialData.setFontFamily('Courier New')
        self.serialData.setMinimumSize(MINWIDTH, 400)
        self.receiveData = True
        
    def appendSerialText(self, appendText):
        if not self.receiveData:
            return
        self.serialData.moveCursor(QtGui.QTextCursor.End)
        self.serialData.insertPlainText(appendText)
        self.serialData.moveCursor(QtGui.QTextCursor.End)

    def setReceiveData(self, checked):
        if checked:
            self.receiveData = True
        else:
            self.receiveData = False
            self.serialData.clear()

app = QtWidgets.QApplication(sys.argv)
w = MainWindow()
app.exec()