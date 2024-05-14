import threading
import time

class Servo():
    def __init__(self):
        self.value = 0

class StoppableThread(threading.Thread):
    def __init__(self, servo, direction):
        super().__init__()
        self._stop_event = threading.Event()
        self.servo = servo
        self.direction = direction

    def run(self):
        while not self._stop_event.is_set():
            # print("Thread is running...")
            if self.direction == 0:
                self.servo.value += 1
            elif self.direction == 1:
                self.servo.value -= 1
        print("Thread was stopped.")

    def stop(self):
        self._stop_event.set()

servo = Servo()
# used = 0
# Create and start the thread
thread1 = StoppableThread(servo, 0)
thread1.start()

print(thread1.is_alive())

# thread2 = StoppableThread(servo, 1)
# thread2.start()
if not thread1.is_alive():
    print("start")
    thread1 = StoppableThread(servo, 0)
    thread1.start()

print(servo.value)

# Stop the thread later
time.sleep(1)
thread1.stop()
thread1.join()  # Wait for the thread to actually finish

print(thread1.is_alive())

if not thread1.is_alive():
    print("start")
    thread1 = StoppableThread(servo, 0)
    thread1.start()

time.sleep(1)
thread1.stop()
thread1.join()  # Wait for the thread to actually finish
print("stop")
thread1.stop()
thread1.join()  # Wait for the thread to actually finish
print("stop")
thread1.stop()
thread1.join()
print("stop")
# # Stop the thread later
# time.sleep(1)
# thread2.stop()
# thread2.join()  # Wait for the thread to actually finish

print(servo.value)