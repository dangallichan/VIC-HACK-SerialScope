# waveMage
## Python-based live sensor-data streaming via USB Serial
<img src="https://github.com/dangallichan/VIC-HACK-SerialScope/assets/71603024/c4c5dec4-909b-493a-914e-b8c793a8df60" width="300">

Our project for the 2024 VIC-HACK - https://github.com/Lewis-Kitchingman/VIC-HACK-2024

We wanted to create a Python-based 'oscilloscope'-like software that allows live viewing of data streaming from a microcontroller connected over USB to your computer.

The code currently assumes all data is transmitted in a single serial 'line' as ASCII text, with commas separating the variables. The first variable may or may not be time, and the maximum number of channels is set to 12.

We made some effort to try to make it 'just work', so it attempts to autodetect a connecting COM port, then process 10 lines to attempt to guess how many channels there are and whether or not the first channel is time. It also attempts to autodect the time scaling factor (i.e. are you using s, ms or us). Obviously not all conditions have been tested, so you may still need to fiddle a bit to make your own version work.

This is what the GUI looks like at the moment:
![waveMageDemo](https://github.com/dangallichan/waveMage-SerialScope/assets/151062386/ac1d2583-662c-40b0-8edb-945d830081fd)

### Required packages
matplotlib, PyQt5, numpy

### Getting started on Linux
On Windows systems the default COM behaviour is to allow read and write access by default. On Linux, ports are considered owned objects with dedicated (and by default, unpriveleged) permissions. A connected arduino or micro:bit will be assigned an abstract control model (ACM) port. To temporarily change the permissions of an ACM port, you can use the chmod command. This method is straightforward but will only last until the device is reconnected or the system is rebooted. For instance, to give all users read and write access to /dev/ttyACM0, you can run the following command:
```
sudo chmod a+rw /dev/ttyACM0
```
Disconnection or power cycling the device will cause these permissions to lapse, required repeated entry of this command (with potentially a different port being assigned each time). To make the permission changes persistent, you need to create a udev rule. Udev rules are used to manage device nodes in /dev dynamically. By creating a custom udev rule, you can ensure that the correct permissions are applied every time the ACM device is connected.
1. Create a udev rule file:
Open a new file in the `/etc/udev/rules.d/` directory. The filename should end with .rules, for example, `99-usb-serial.rules`:
```
sudo nano /etc/udev/rules.d/99-usb-serial.rules
```
2. Add the udev rule:
Insert a rule to match the ACM device and set the desired permissions. For example:
```
KERNEL=="ttyACM[0-9]*", MODE="0666"
```
This rule matches all devices with names starting with ttyACM followed by a number, and it sets the permissions to 0666, granting read and write access to all users.
3. Reload udev rules:
After saving the file, reload the udev rules to apply the changes:
```
sudo udevadm control --reload-rules
sudo udevadm trigger
```
Doing this will ensure that all ACM devices (at least, those from ports 0-9) will have read and write access indefinitely.

### Want to stream data from a micro:bit?
The easiest way is to put this code onto your micro:bit: https://github.com/dgallichan/microbit-simpleserial-trace

Once you understand the basics, here is some starting code that lets you have much more control over the data being sent: https://github.com/dgallichan/microbit-serialSendData

### Inspiration
Existing packages/sources that we pooled various bits and pieces from:
* https://github.com/arnaudhe/python-scope
* https://github.com/jscastonguay/py-serial-scope/blob/master/pySerialScope.py
* https://pypi.org/project/SerialScope/
* https://learn.sparkfun.com/tutorials/graph-sensor-data-with-python-and-matplotlib/introduction
* https://github.com/xioTechnologies/Serial-Oscilloscope (Windows App)

I also had previously made something with less GUI-ness for MATLAB here:
https://github.com/dgallichan/matlab-serialScope

