
import time
import multiprocessing
import select
import random

def sleepy(i, queue):
    time.sleep(i)
    print(f"{i} has awoken")
    queue.put(i)

def consumer(q1, q2, q3):
    woke = [False, False, False]
    while True:
        (inputs, _, _) = select.select([q1._reader, q2._reader, q3._reader], [], [])
        if q1._reader in inputs:
             _ = q1.get()
             woke[0] = True
        elif q2._reader in inputs:
             _ = q2.get()
             woke[1] = True
        elif q3._reader in inputs:
             _ = q3.get()
             woke[2] = True
        if all(i for i in woke):
             print("All have awoken")
             return

q1 = multiprocessing.Queue()
q2 = multiprocessing.Queue()
q3 = multiprocessing.Queue()

processes = [
    multiprocessing.Process(
        target=sleepy, 
        args=(1, q1)
    ),
    multiprocessing.Process(
        target=sleepy, 
        args=(2, q2)
    ),
    multiprocessing.Process(
        target=sleepy, 
        args=(3, q3)
    ),
    multiprocessing.Process(
        target=consumer, 
        args=(q1, q2, q3)
    )
]


for process in processes:
    process.start()

for process in processes:
    process.join()
