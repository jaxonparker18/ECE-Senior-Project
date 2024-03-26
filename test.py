from gpiozero import Servo
import numpy as np
from time import sleep

servo = Servo("BOARD32")

while True:
    servo.min()
    sleep(1)
    servo.mid()
    sleep(1)
    servo.max()
    sleep(1)
