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

       res = executor.map(do_sleep, seconds)

       for r in res:
           print(r)
    end = time.perf_counter()
            
    print(f'finished in {round(end - start, 2)} seconds')