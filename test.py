from gpiozero import PWMLED

led = PWMLED("BOARD32")

while True:
    led.value = 1