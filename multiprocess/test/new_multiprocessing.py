import concurrent.futures
import time

def do_sleep(seconds):
    print(f'I am sleeping for {seconds} of seconds')
    time.sleep(seconds)
    return f'Done sleeping... {seconds}'


if __name__ == "__main__":
    start = time.perf_counter()
    seconds  = [i for i in range(4, 0, -1)]
    print(seconds)

    with concurrent.futures.ProcessPoolExecutor() as executor:
        results = [executor.submit(do_sleep, sec) for sec in seconds]
        for process in concurrent.futures.as_completed(results):
            print(process.result())
    
    end = time.perf_counter()
            
    print(f'finished in {round(end - start, 2)} seconds')