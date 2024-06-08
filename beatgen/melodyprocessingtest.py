# melodydata.py
import random
# natural minor
n = {
    0: [1, 5, 8, 1, 5, 2, 5, 2, 1, 8, 3, 5],
    1: [5, 3, 3, 4, 5, 5, 5, 3, 3, 3, 2, 3, 3, 5, 3, 5, 6, 4, 5],
    2: [1, 1, 1, 1, 4, 1, 1, 2, 1, 4],
    3: [4, 5, 1, 5, 1, 1, 1, 5, 5, 2, 2, 5, 2, 5, 5, 5, 2],
    4: [2, 5, 8, 6, 3, 5, 5, 8, 1, 5],
    5: [6, 1, 6, 4, 6, 1, 3, 3, 3, 3, 3, 2, 2, 4, 3, 1, 1, 5, 1, 1, 1, 6, 2, 4],
    6: [4, 8, 1, 5, 5, 4],
    7: [6],
    8: [5, 8, 5, 4, 7]
}

timebase = random.choice([1, 2, 2, 2, 2, 2, 2, 4, 4, 4, 4, 4, 4, 4, 4, 8])

l = [random.choice(n[0])]
t = l[0]
for _ in range(int(16 / timebase - 1)):
    if random.random() > 0.25:
        t = random.choice(n[t])
        l.append(t)
    else:
        l.append(0)

harmony = []
for i in l:
    if i != 0 and random.random() > 0.5:
        harmony.append(random.choice(n[i]) + 7)
    else:
        harmony.append(0)

def change(melody):
    return melody

print(list(zip(l, harmony)))