
import multiprocessing

def producer(queue):
    for i in range(5):
        queue.put(i)

def doubler(queue_in, queue_out):
    while True:
        data = queue_in.get()
        data = data * 2
        queue_out.put(data)

def consumer(queue):
    while True:
        data = queue.get()
        print(data)

def produce_and_double(queue):
    internal_queue = multiprocessing.Queue()
    internal_processes = [
        multiprocessing.Process(
            target=producer, 
            args=(internal_queue,)
        ),
        multiprocessing.Process(
            target=doubler, 
            args=(internal_queue, queue)
        )
    ]
    
    for process in internal_processes:
        process.start()


p_to_d_queue = multiprocessing.Queue()
d_to_c_queue = multiprocessing.Queue()

single = 0
if single:
    processes = [
        multiprocessing.Process(
            target=producer, 
            args=(p_to_d_queue,)
        ),
        multiprocessing.Process(
            target=doubler, 
            args=(p_to_d_queue, d_to_c_queue)
        ),
        multiprocessing.Process(
            target=consumer, 
            args=(d_to_c_queue,)
        )
    ]
else:
    processes = [
        multiprocessing.Process(
            target=produce_and_double, 
            args=(d_to_c_queue,)
        ),
        multiprocessing.Process(
            target=consumer, 
            args=(d_to_c_queue,)
        )
    ]

for process in processes:
    process.start()

for process in processes:
    process.join()
