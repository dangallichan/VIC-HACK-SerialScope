import serial
import numpy
import scipy
from matplotlib import pyplot as plt

#setup
ser = serial.Serial('/dev/ttyACM0', 115200) #define port and protocol
testread = ser.readline().decode('ascii')               #read one line and infer channels off of number of commas
#channels = testread.count(',')                         #data prototype = timestamp, channel 1, channel 2, ..., channel n (line termination = newline)
channels = 6
blocksize = 1000                                        #no of samples to be read and processed in each frame
LP_cutoff = numpy.array([20, 20, 20, 20, 20, 20])       #cutoff frequency of low pass filter (one per channel)
filter_order = 4                                        #IIR filter order
sos = numpy.empty((channels, 2, 6))
sensor_samplerate = 100                                 #samplerate of the sensor providing the data to be read (used for filter calculations)
prev_data = numpy.zeros((10, channels+1))

# design filter coefficients
for f in range(channels):
    sos[f, :, :] = scipy.signal.butter(filter_order, LP_cutoff[0], btype='low', analog=False, output='sos', fs=sensor_samplerate)

for i in range(2):
    #get dataframe
    smpls = 0
    data_in = numpy.empty((blocksize, channels + 1))
    data_filtered = numpy.empty((blocksize, channels + 1))
    data_prefft = numpy.empty((blocksize, channels + 1))
    while smpls < blocksize:
        inBuff = ser.readline().decode('ascii').partition(' ')[0]
        inBuff = numpy.fromstring(inBuff, dtype=float, sep=',')
        data_in[smpls, :] = inBuff
        smpls = smpls + 1

    #filter
    data_in = numpy.concatenate((prev_data, data_in), 0)
    for c in range(channels):
        data_filtered[:, c] = scipy.signal.sosfilt(sos[c, :, :], data_in[:, c])[10:]

    prev_data = data_filtered[-10:, :]

    #add ~.1Hz high pass prior to fft to remove DC
    sos_fft = scipy.signal.butter(filter_order, .1, btype='high', analog=False, output='sos', fs=sensor_samplerate)
    for c in range(channels):
        data_prefft[:, c] = scipy.signal.sosfilt(sos_fft, data_in[10:, c]) * numpy.hamming(blocksize)
    ffts = numpy.fft.fft(data_prefft, 100, 0)

plt.plot(numpy.abs(ffts[:, 3]))
#plt.plot(data_in[10:, 3])
#plt.plot(data_filtered[:, 3])
plt.show()