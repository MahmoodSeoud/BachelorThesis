
import time
import multiprocessing

def pingpong(i, input, output, initial_data=""):
    if initial_data:
        output.send(initial_data)
    while True:
        data = input.recv()
        time.sleep(1)
        print(data)
        output.send(data)

pipe_1_in, pipe_1_out  = multiprocessing.Pipe()
pipe_2_in, pipe_2_out  = multiprocessing.Pipe()

processes = [
    multiprocessing.Process(
        target=pingpong, 
        args=(0, pipe_1_in, pipe_2_out, "hello")
    ),
    multiprocessing.Process(
        target=pingpong, 
        args=(1, pipe_2_in, pipe_1_out)
    )
]

for process in processes:
    process.start()

for process in processes:
    process.join()
