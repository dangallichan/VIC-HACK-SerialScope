import sys
import random
import matplotlib 
matplotlib.use('QtAgg')

import numpy as np

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import Qt

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar


# from matplotlib.figure import Figure
from matplotlib import pyplot as plt

# SER_TIMEOUT = 0.1                   # Timeout for serial Rx
# baudrate    = 115200                # Default baud rate
# portname    = "COM11"                # Default port name



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
        self.n_channels = 3

        self.useRandomData = True
        if self.useRandomData:
            self.xdata = np.linspace(1, self.n_xpts, self.n_xpts)
            self.ydata = np.random.randint(10, size=(self.n_xpts, self.n_channels))
        
        self.Yoffset = 0

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
        self.YGlobalScale = self.slYGlobalScale.value() / 10

        
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

        self.show()

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


    def valuechange(self):
        # obtain value from slider
        # self.ax1.set_ylim(self.n_channels*self.slOffset.value())
        self.Yoffset = self.slYOffset.value()
        self.YGlobalScale = self.slYGlobalScale.value() / 10

    def update_plot(self):
        # Drop off the first y element, append a new one.
        self.ydata = np.roll(self.ydata, -1, axis=0)
        if self.useRandomData:
            self.ydata[-1,:] = np.random.randint(10, size=(1, self.n_channels))

       
        # We have a reference, we can use it to update the data for that line.
        for iPlot in range(self.n_channels):
            self._plot_refs[iPlot].set_ydata(self.YGlobalScale * self.ydata[:,iPlot] + self.Yoffset*iPlot)

        # Trigger the canvas to update and redraw.
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()

app = QtWidgets.QApplication(sys.argv)
w = MainWindow()
app.exec()