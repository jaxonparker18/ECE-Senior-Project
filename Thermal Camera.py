# sudo pip3 install matplotlib
# sudo pip3 install scipy
# sudo apt-get install -y python-smbus
# sudo apt-get install -y i2c-tools
# sudo pip3 install RPI.GPIO adafruit-blinka
# sudo pip3 install adafruit-circuitpython-mlx90640
# sudo apt-get install -y python-smbus

import time
import board
import busio
import numpy as np
import adafruit_mlx90640
import matplotlib.pyplot as plt

i2c = busio.I2C(board.SCL, board.SDA)
mlx = adafruit_mlx90640.MLX90640(i2c)
mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_4_HZ  # Set to a feasible refresh rate

plt.ion()
fig, ax = plt.subplots(figsize=(12, 7))
therm1 = ax.imshow(np.zeros((24, 32)), vmin=0, vmax=60)
cbar = fig.colorbar(therm1)
cbar.set_label('Temperature [$^{\circ}$C]', fontsize=14)

frame = np.zeros((24 * 32,))
t_array = []
max_retries = 5

while True:
    t1 = time.monotonic()
    retry_count = 0
    while retry_count < max_retries:
        try:
            mlx.getFrame(frame)
            data_array = np.reshape(frame, (24, 32))
            therm1.set_data(np.fliplr(data_array))
            therm1.set_clim(vmin=np.min(data_array), vmax=np.max(data_array))
            fig.canvas.draw()  # Redraw the figure to update the plot and colorbar
            fig.canvas.flush_events()
            plt.pause(0.001)
            t_array.append(time.monotonic() - t1)
            print('Sample Rate: {0:2.1f}fps'.format(len(t_array) / np.sum(t_array)))
            break
        except ValueError:
            retry_count += 1
        except RuntimeError as e:
            retry_count += 1
            if retry_count >= max_retries:
                print(f"Failed after {max_retries} retries with error: {e}")
                break