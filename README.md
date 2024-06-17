# waveMage
<img src="https://github.com/dangallichan/VIC-HACK-SerialScope/assets/71603024/c4c5dec4-909b-493a-914e-b8c793a8df60" width="300">

Our project for the 2024 VIC-HACK - https://github.com/Lewis-Kitchingman/VIC-HACK-2024

We wanted to create a Python-based 'oscilloscope'-like software that allows live viewing of data streaming from a microcontroller connected over USB to your computer.

The code currently assumes all data is transmitted in a single serial 'line' as ASCII text, with commas separating the variables. The first variable may or may not be time, and the maximum number of channels is set to 12.

We made some effort to try to make it 'just work', so it attempts to autodetect a connecting COM port, then process 10 lines to attempt to guess how many channels there are and whether or not the first channel is time. It also attempts to autodect the time scaling factor (i.e. are you using s, ms or us). Obviously not all conditions have been tested, so you may still need to fiddle a bit to make your own version work.

This is what the GUI looks like at the moment:
![waveMageDemo](https://github.com/dangallichan/waveMage-SerialScope/assets/151062386/ac1d2583-662c-40b0-8edb-945d830081fd)

### Required packages
matplotlib, PyQt5, numpy

### Inspiration
Existing packages/sources that we pooled various bits and pieces from:
* https://github.com/arnaudhe/python-scope
* https://github.com/jscastonguay/py-serial-scope/blob/master/pySerialScope.py
* https://pypi.org/project/SerialScope/
* https://learn.sparkfun.com/tutorials/graph-sensor-data-with-python-and-matplotlib/introduction
* https://github.com/xioTechnologies/Serial-Oscilloscope (Windows App)

I also had previously made something with less GUI-ness for MATLAB here:
https://github.com/dgallichan/matlab-serialScope

