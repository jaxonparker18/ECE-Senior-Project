#!/usr/bin/python
#--------------------------------------
#    ___  ___  _ ____
#   / _ \/ _ \(_) __/__  __ __
#  / , _/ ___/ /\ \/ _ \/ // /
# /_/|_/_/  /_/___/ .__/\_, /
#                /_/   /___/
#
#           servo3.py
# Example script to control a servo
# connected to GPIO17 using the Gpiozero library.
# Allows tweaking of pulse widths to get the full
# range of movement.
# Uses "value" to move between min and max rotation.
#
# Use CTRL-C to break out of While loop.
#
# Author : Matt Hawkins
# Date   : 20/01/2018
#
# https://www.raspberrypi-spy.co.uk/tag/servo/
#
#--------------------------------------
from gpiozero import Servo 
from gpiozero import PWMLED
from time import sleep
import numpy

correctionMAX = 0.5
correctionMIN = 0.5
maxPW = (2.0 + correctionMAX)/1000
minPW = (1.0 - correctionMIN)/1000

led = Servo(17, min_pulse_width=minPW, max_pulse_width=maxPW)
print(led.max_pulse_width)
num = 0

while True:

    """
    print("Set value range -1.0 to +1.0")
    for value in range(0,21):
        value2=(float(value)-10)/10
        led.value=value2
        print("expected:" + str(value2))
        print("actual:" + str(led.value))
        sleep(0.5)
        
    print("Set value range +1.0 to -1.0")
    for value in range(20, -1, -1):
        value2=(float(value)-10)/10
        led.value=value2
        print("expected:" + str(value2))
        print("actual:" + str(led.value))
        sleep(0.5)
    """
    
    ## Increment Test for Servo
    """
    if num >= 1.0:
        num = -1.0
    led.value = num
    num += 0.025
    
    print("expec: " + str(num))
    print("actual: " + str(led.value))
    sleep(0.05)
    """
    
    ## Min. and Max. Test for Servo

    led.min()
    print("expec: " + str(num))
    print("actual: " + str(led.value))
    sleep(1)
    led.max()
    print("expec: " + str(num))
    print("actual: " + str(led.value))
    sleep(1)
    
    ## Exact Value Test for Servo
    """
    led.value = -1.0
    print("expec: " + str(-1.0))
    print("actual: " + str(led.value))
    sleep(1)
    led.value = -0.8
    print("expec: " + str(-0.8))
    print("actual: " + str(led.value))
    sleep(1)
    led.value = -0.4
    print("expec: " + str(-0.4))
    print("actual: " + str(led.value))
    sleep(1)
    led.value = 0.0
    print("expec: " + str(0.0))
    print("actual: " + str(led.value))
    sleep(1)
    led.value = 0.4
    print("expec: " + str(0.4))
    print("actual: " + str(led.value))
    sleep(1)
    led.value = 0.8
    print("expec: " + str(0.8))
    print("actual: " + str(led.value))
    sleep(1)
    led.value = 1.0
    print("expec: " + str(1.0))
    print("actual: " + str(led.value))
    sleep(1)
    """
    
    ## Nathan's Original Test Code
    """
    for duty_cycle in range(0, 100, 1):
        led.value = duty_cycle/100.0
        print("expec: " + str(duty_cycle/100.0))
        print("actual: " + str(led.value))
        sleep(0.1)
    """
