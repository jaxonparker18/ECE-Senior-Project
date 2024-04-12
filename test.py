from gpiozero import Servo
from gpiozero import LED
from gpiozero import PWMLED
import numpy as np
from time import sleep
import serial

# servo = PWMLED("BOARD32")

serial_port = '/dev/ttyUSB0'
baud_rate = 115200
ser = serial.Serial(serial_port, baud_rate)
x = ""
while True:
    for i in range(5):
        x += ser.read().decode('utf-8')
    print(x)
    x = ""

# pin = PWMLED("BOARD8")
# pin2 = PWMLED("BOARD10")
# pin.value = 0
# pin2.value = 0
# v = 0
# while True:
#    sleep(1)
#    print(v)
#    v += 0.1
#    if v > 1:
#        v = 0
#    pin.value = v
#    pin2.value = v


