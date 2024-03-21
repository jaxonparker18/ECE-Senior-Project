a, b, c = "101"

apples = 2

def t():
    a = "2"
    global apples
    apples = 4

t()
a = int(apples)


print(a)
