import multiprocessing
import random
import time

NUM_REINDEER = 9
NUM_ELFS = 10

system_runs = 0
milestone = 100
endGoal = 1000

# Santa is the consumer
def santa(reindeer_conn, reindeer_cond, elf_conn, elf_cond):
    while True:

        if(reindeer_conn.poll()): # Checking if there is anything to read
            print(reindeer_conn.recv()) # Waiting for the last reindeer to wake Santa up
 #           time.sleep(1) # Simulating their work

            with reindeer_cond:
                reindeer_cond.notify_all() # Tell everybody that its time to go back to holiday

            print('Reindeer can get back on holiday')
            global system_runs
            system_runs += 1

            if system_runs % milestone == 0:
                print(f'System reached {system_runs} runs')

        elif (elf_conn.poll()): # Checking if there is anything to read
            print(elf_conn.recv()) # Waiting for 3 Elfs to arrive with a problem
#            time.sleep(1) # Simulating Santa helping Elfs
            

            with elf_cond:
                elf_cond.notify_all() # Tell everybody that its time to go back to holiday

            print('Elfs can get back to work')
            global system_runs
            system_runs += 1
        
            if system_runs % milestone == 0:
                print(f'System reached {system_runs} runs')



# Reindeers are producers
def reindeer(reindeer_id, reindeer_conn, reindeer_cond, reindeer_queue, reindeer_lock):
    while True:
        sleep_time = random.randint(1,5)
        time.sleep(sleep_time) # Simulating that they are sleeping a random amount of time

        # Beginning of critical section
        with reindeer_lock:
            reindeer_queue.put(reindeer_id)
            print(f'Reindeer {reindeer_id} is now awake after {sleep_time} seconds')

            if reindeer_queue.full():
                while not reindeer_queue.empty():
                    last_reindeer = reindeer_queue.get()       
                reindeer_conn.send(f'Santa! All reindeers are awake - Reindeer {last_reindeer}')
        # Ending of critical section
        
        # Waiting for reindeer to tell Santa and for Santa to give us holiday
        with reindeer_cond:
            reindeer_cond.wait()

# Another set of producers processes
def elf(elf_id, elf_queue, elf_lock, elf_conn, elf_cond, elf_one, elf_two, elf_three):
    while True:
        work_time = random.randint(5,10)
        time.sleep(work_time) # Simulating that they are out 
                              #working, once done with sleep is when the encounter a problem
        
        with elf_lock:
            elf_queue.put(elf_id)
            print(f'Elf {elf_id} has a problem')

            if elf_queue.full(): 
                while not elf_queue.empty():
                    elf_one.value = elf_queue.get()
                    elf_two.value = elf_queue.get()
                    elf_three.value = elf_queue.get()
                elf_conn.send(f'Elfs: {elf_one.value, elf_two.value, elf_three.value} are saying: "Santa wake up! we are having problems"')

        # Waiting for reindeer to tell Santa and for Santa to give us holiday
        with elf_cond:
            elf_cond.wait()

if __name__ == "__main__":

    # Reindeer multiprocessing items
    reindeer_conn1, reindeer_conn2 = multiprocessing.Pipe()
    reindeer_queue = multiprocessing.Queue(NUM_REINDEER)
    reindeer_cond = multiprocessing.Condition()
    reindeer_lock = multiprocessing.Lock()

    # elf multiprocessing items
    elf_conn1, elf_conn2 = multiprocessing.Pipe()
    elf_queue = multiprocessing.Queue(3)
    elf_cond = multiprocessing.Condition()
    elf_lock = multiprocessing.Lock()
    elf_one = multiprocessing.Value('i', 0)
    elf_two = multiprocessing.Value('i', 0)
    elf_three = multiprocessing.Value('i', 0)

    # Constructing the processes
    santa_process = multiprocessing.Process(target=santa, args=(reindeer_conn2, reindeer_cond, elf_conn2, elf_cond))
    reindeer_processes = [multiprocessing.Process(target=reindeer, args=(i, reindeer_conn1, reindeer_cond, reindeer_queue, reindeer_lock)) for i in range(1,NUM_REINDEER+1)]
    elf_processes = [multiprocessing.Process(target=elf, args=(i, elf_queue, elf_lock, elf_conn1, elf_cond, elf_one, elf_two, elf_three)) for i in range(1, NUM_ELFS+1)]

    # Starting the processes
    for reindeer_process in reindeer_processes:
        reindeer_process.start()
    for elf_process in elf_processes:
        elf_process.start()
    santa_process.start()

    # Joining the processes -  might delete later
    for reindeer_process in reindeer_processes:
        reindeer_process.join()
    for elf_process in elf_processes:
        elf_process.join()
    santa_process.join()