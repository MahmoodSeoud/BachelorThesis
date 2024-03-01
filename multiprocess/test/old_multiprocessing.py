import multiprocessing as mp
import time

def do_sleep(seconds):
    print(f'I am sleeping for {seconds} of seconds')
    time.sleep(seconds)


if __name__ == "__main__":
    
    processes = []
    start = time.perf_counter()
    for _  in range(10):
        p = mp.Process(target=do_sleep, args=[1])
        p.start()
        processes.append(p)


    for process in processes:
        p.join()
    end = time.perf_counter()
    print(f'Process done in {round(end - start, 2)}')