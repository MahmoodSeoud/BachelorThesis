import socket
import socketserver
import threading
import time
import random
import bisect
import json
from enum import Enum

class MSG_TYPE(Enum):
    SANTA = 1
    FEELER = 2
    ACKNOWLEDGEMENT = 3
    REJECT = 4
    READY_REQUEST = 5
    READY_RESPONSE = 6
    

NUM_ELVES = 4
NUM_CHAIN = 3
LOCAL_HOST = "127.0.0.1"
SANTA_PORT = 29800

class RequestHandler(socketserver.StreamRequestHandler):
    def __init__(self, Elf, *args, **kwargs):
        self.Elf = Elf
        super().__init__(*args, **kwargs)

    def handle(self):
        
        # Receive the message type
        data_bytes = self.request.recv(1024)
        # Decode bytes to a string and convert it to a dictionary
        payload = json.loads(data_bytes.decode('utf-8'))
        # Access msg_type from the dictionary
        msg_type = payload['type']

        if msg_type == MSG_TYPE.SANTA._value_: # Handle a string message from Santa
            pass

        elif msg_type == MSG_TYPE.FEELER._value_:  # Handle a tuple message from other Elf
            peer_id = payload['id']
            peer_port = payload['port']
            peer_sleep_time = payload['sleep_time']

            peer_triple = (peer_sleep_time, peer_id, peer_port)
            my_triple = (self.Elf.sleep_time, self.Elf.id ,self.Elf.port)
            print(f'ELF {self.Elf.id} - RECIEVED THE FEELER FROM ELF {peer_id}')

            with self.Elf.lock:
                if self.Elf.sleep_time == peer_sleep_time:
                    data = {
                        'type': MSG_TYPE.REJECT._value_,
                    }
                else:

                    data = {
                        'type': MSG_TYPE.ACKNOWLEDGEMENT._value_,
                        'chain': [peer_triple, my_triple]
                    }

            # Message to Ack that the feeler was sent out.
            buffer = self.Elf.create_buffer(data)
            self.Elf.send_message(LOCAL_HOST, peer_port, buffer)

        elif msg_type == MSG_TYPE.ACKNOWLEDGEMENT._value_: # Handle the case of acceptance
            chain = payload['chain']
            peer_sleep_time = chain[1][0]
            peer_id = chain[1][1]
            peer_port = chain[1][2]

            if self.Elf.id == 1 or self.Elf.id == 4:
                print(f'ELF {self.Elf.id} - RECIEVED THE ACKNOWLEDGEMENT FROM ELF {peer_id}') 
                print(f'ELF {self.Elf.id} - RECIEVED THE CHAIN: {chain} FROM ELF {peer_id}')
            

            #my_triple = (my_sleep_time, my_id, my_port) # Maybe i dont need this one here
            peer_triple = (peer_sleep_time, peer_id, peer_port)
            my_triple = (self.Elf.sleep_time, self.Elf.id , self.Elf.port)

            with self.Elf.lock:
                if len(self.Elf.chain) < NUM_CHAIN:
                    if peer_triple not in self.Elf.chain:
                        bisect.insort(self.Elf.chain, peer_triple)

                    if my_triple not in self.Elf.chain: 
                        bisect.insort(self.Elf.chain, my_triple)
                
                first_elf_in_chain_id = self.Elf.chain[0][1]

                # Do we THINK we have enough elves? Only the "root" can be root
                if len(self.Elf.chain) == NUM_CHAIN and first_elf_in_chain_id == self.Elf.id:
                    self.Elf.is_chain_root = True
                    print(f'Elf {self.Elf.id} - I am Groot') # Xd 
                    print(f'ELF {self.Elf.id} - I ROOT OF THE CHAIN {self.Elf.chain}')
                else:
                    self.Elf.is_chain_root = False


                # If len(self.Elf.chain) == NUM_ELVES, then I we 
                # have enough elves to ask them if ready
                if len(self.Elf.chain) == NUM_CHAIN and self.Elf.is_chain_root:
                    msg_type = MSG_TYPE.READY_REQUEST._value_ 
                    data = {
                        'type': msg_type,
                        'peer_port': self.Elf.port
                    }
                    buffer = self.Elf.create_buffer(data)


                    for elf in self.Elf.chain:
                        peer_port = elf[2] #port
                        if peer_port != self.Elf.port: # Send to all the other elves if they are
                            self.Elf.send_message(LOCAL_HOST, peer_port, buffer)
                    

        elif msg_type == MSG_TYPE.READY_REQUEST._value_:
            peer_port = payload['peer_port']

            msg_type = MSG_TYPE.READY_RESPONSE._value_ 

            with self.Elf.lock:
                data = {
                    'type': msg_type,
                    'is_chain_member': int(self.Elf.is_chain_member),
                    'peer_id': self.Elf.id
                }
                self.Elf.is_chain_member = True

            buffer = self.Elf.create_buffer(data)
            self.Elf.send_message(LOCAL_HOST, peer_port, buffer)


        elif msg_type == MSG_TYPE.READY_RESPONSE._value_: 
            ready = payload['is_chain_member']
            peer_id = payload['peer_id']

            #print(f'Elf{peer_id}{" was" if ready else " was not"} ready')
            #print(f'Elf {self.Elf.id} the chain is ', self.Elf.chain)

            if ready:
                with self.Elf.lock:
                    # Check if the responding elf is already a member of another chain
                    for elf in self.Elf.chain:
                        if elf[1] == peer_id and elf[2] != self.Elf.port:
                            # The elf is a member of another chain, drop the current chain and start over
                            self.Elf.chain = []
                            self.Elf.is_chain_root = False
                            break
            
        elif msg_type == MSG_TYPE.REJECT._value_:
            print('Already taken')
            pass


class Elf:
    def __init__(self, id, ip, port, peer_ports):
        self.id = id
        self.ip = ip
        self.port = port
        self.peer_ports = peer_ports
        self.sleep_time = 0
        self.lock = threading.Lock()
        self.chain = []
        self.is_chain_root = False
        self.is_chain_member = False
        self.condition = threading.Condition()
        self.barrier = threading.Barrier(NUM_CHAIN - 1)


    def elf_listener(self):
        # Start server side
        # Passing in *args and **kwargs to give the Requesthandler access to all the Elfs attributes
        with socketserver.ThreadingTCPServer((self.ip, self.port), lambda *args, **kwargs: RequestHandler(self, *args, **kwargs)) as server:
            print(f"EL: {self.id} -  Starting elve listener: {self.ip}:{self.port}")
            try: 
                server.serve_forever()
            finally:
                server.server_close()

    """ STUPID TEST CAN BE REMOVED WHEN DONE TESTING"""
    def find_sleeping_time_testing(self):
        sleeping_time = 0

        if (self.id == 1):
            sleeping_time = 3
        elif (self.id == 2):
            sleeping_time = 4
        elif (self.id == 3):
            sleeping_time = 5
        elif (self.id == 4):
            sleeping_time = 3

        return sleeping_time


    def elf_writer(self):
        while True:
            self.sleep_time =  self.find_sleeping_time_testing()   #random.randint(3,5) # Updating the sleeping time
            time.sleep(self.sleep_time)  # Simulate elf working
            print(f'Elf {self.id} has problems after {self.sleep_time} seconds')

            # If the elf is not forming a group, initiate group formation
            # Send message to peers about group formation
            msg_type = MSG_TYPE.FEELER._value_

            data = {
                'type': msg_type,
                'id': self.id,
                'sleep_time': self.sleep_time,
                'port': self.port
            }

            buffer = self.create_buffer(data)

            # Msg all the other elves about presence of chain root
            for peer_port in self.peer_ports:
                if peer_port != self.port:
                    self.send_message(LOCAL_HOST, peer_port, buffer)

            # Waiting for all the threads to sync
            with self.condition:
                self.condition.wait()

    def create_buffer(self, payload):
        buffer = json.dumps(payload).encode('utf-8')
        return buffer

    def send_message(self, host, port, message):
        try:
            #print(f'EW {self.id} - connecting to {port}:{port}')
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as conn_socket:
                conn_socket.connect((host, port))
                conn_socket.sendall(message)

        except ConnectionRefusedError:
            print(f"EW {self.id} - Couldn't connect to " f"{self.ip}:{host}. Will try again in 3 seconds.")

    def start_thread(self):
        sub_threads = [
            threading.Thread(target=self.elf_listener),
            threading.Thread(target=self.elf_writer)
            ]
        for thread in sub_threads:
            thread.start()
        for thread in sub_threads:
            thread.join()

if __name__ == "__main__":

    peer_ports = [ 44441 + i for i in range(0, NUM_ELVES)]

    elve_threads = [
        threading.Thread(
            target=Elf(
                i+1, 
                LOCAL_HOST,
                peer_ports[i],
                peer_ports).start_thread,
            daemon=True
        ) for i in range(NUM_ELVES)
    ]

    for elve_thread in elve_threads:
        elve_thread.start()

    for elve_thread in elve_threads:
        elve_thread.join()

