from rpi_hardware_pwm import HardwarePWM
from time import sleep

pwm = HardwarePWM(pwm_channel=2, hz=50, chip=2)

## MAX PWM IS 2.4MS or 12% DUTY CYCLE
## MIN PWM IS 0.8MS or  4% DUTY CYCLE

pwm.start(12)
num = 12
sleep(1)
while True:
	
	if num <= 4:
		sleep(1)
		pwm.change_duty_cycle(12)
		num = 12	
		sleep(1)	
	num -= 0.05
	pwm.change_duty_cycle(num)
    
	print("expected: " + str(num))
	sleep(0.02)
