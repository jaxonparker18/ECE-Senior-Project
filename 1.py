import time
def test(v):
    if v:
        print("v is true")
    else:
        print("v is false")

def set_true(x):
    x = True

b = False

test(b)
time.sleep(1)
set_true(b)
time.sleep(1)
test(b)