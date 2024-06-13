import serial
import numpy as np
ser = serial.Serial('/dev/ttyACM0', baudrate=115200)
barr = ser.readline()
#barr = b'127.50,-45.00,42.50\r\n'
floats =  np.array([float(a) for a in str(barr[:-3], 'ascii').split(",")])
shape = np.size(floats)
chunk_size = 10
data = np.zeros((shape, chunk_size))
ctr = 0
chunk_ctr = 1
while ctr < 30:
    chind = chunk_ctr * chunk_size
    if ctr + 2 > chind:
        data.resize((shape, chind+chunk_size))
        print(np.shape(data)) # push your data to your qt object here
        chunk_ctr += 1
    barr = ser.readline()
    floats =  np.array([float(a) for a in str(barr[:-3], 'ascii').split(",")])
    data[:, ctr] = floats
    ctr += 1
    


print(floats)
