import socket
import socketserver
import struct
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
CHAIN_NUM = 3
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
        print('MSG_TYPE', msg_type)

        if msg_type == MSG_TYPE.SANTA._value_: # Handle a string message from Santa
            pass


        elif msg_type == MSG_TYPE.FEELER._value_:  # Handle a tuple message from other Elf
            peer_id = payload['id']
            peer_port = payload['port']
            peer_sleep_time = payload['sleep_time']

            peer_triple = (peer_sleep_time, peer_id, peer_port)
            my_triple = (self.Elf.sleep_time, self.Elf.id ,self.Elf.port)

            #if not self.Elf.is_chain_member:     # Not yet taken
            with self.Elf.lock:
                # bisect.insort uses a binary search algorithm to insert them in ordered way (sleep_time, id)
                if len(self.Elf.chain) < CHAIN_NUM:
                    if peer_triple not in self.Elf.chain:
                        bisect.insort(self.Elf.chain, peer_triple)

                    if my_triple not in self.Elf.chain: 
                        bisect.insort(self.Elf.chain, my_triple)
                    
                data = {
                        'type': MSG_TYPE.ACKNOWLEDGEMENT._value_,
                        'chain': [(elf[0], elf[1], elf[2]) for elf in self.Elf.chain]
                    }

            # Message to Ack that the feeler was sent out.
            buffer = self.Elf.create_buffer(data)
            self.Elf.send_message(LOCAL_HOST, peer_port, buffer)

        elif msg_type == MSG_TYPE.ACKNOWLEDGEMENT._value_: # Handle the case of acceptance

            chain = payload['chain']
            peer_sleep_time = chain[0][0]
            peer_id = chain[0][1]
            peer_port = chain[0][2]

            #my_triple = (my_sleep_time, my_id, my_port) # Maybe i dont need this one here
            peer_triple = (peer_sleep_time, peer_id, peer_port)

            with self.Elf.lock:
                if len(self.Elf.chain) < CHAIN_NUM:
                    if peer_triple not in self.Elf.chain:
                        bisect.insort(self.Elf.chain, peer_triple)

                first_elf_in_chain_id = self.Elf.chain[0][1]

                # Do we THINK we have enough elves? Only the "root" can be root
                if first_elf_in_chain_id == self.Elf.id:
                    self.Elf.is_chain_root = True

                # If len(self.Elf.chain) == NUM_ELVES, then I must be the root
                if self.Elf.is_chain_root:
                    print(f'Elf{self.Elf.id} I am Groot') # Xd 
                    msg_type = MSG_TYPE.READY_REQUEST._value_ 
                    data = {
                        'type': msg_type,
                        'peer_port': self.Elf.port
                    }
                    buffer = self.Elf.create_buffer(data)

                    for elf in self.Elf.chain:
                        peer_port = elf[2] #port
                        if peer_port != self.Elf.port:
                            self.Elf.send_message(LOCAL_HOST, peer_port, buffer)
                    

        elif msg_type == MSG_TYPE.READY_REQUEST._value_:
            peer_port = payload['peer_port']
            print('I gotin here')

            msg_type = MSG_TYPE.READY_RESPONSE._value_ 

            with self.Elf.lock:
                data = {
                    'type': msg_type,
                    'is_chain_member': int(self.Elf.is_chain_member)
                }
                self.Elf.is_chain_member = True

            buffer = self.Elf.create_buffer(data)
            self.Elf.send_message(LOCAL_HOST, peer_port, buffer)


        elif msg_type == MSG_TYPE.READY_RESPONSE._value_: 
            ready = payload['is_chain_member']

            print('Chain:', self.Elf.chain)

            if not ready:
                print(f'Elf{self.Elf.id} got in here')
                self.Elf.chain_root = False

                with self.Elf.lock:
                    self.Elf.chain = []
               # with self.Elf.condition:
               #     self.Elf.condition.notify_all()
            
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


    def elf_listener(self):
        # Start server side
        # Passing in *args and **kwargs to give the Requesthandler access to all the Elfs attributes
        with socketserver.ThreadingTCPServer((self.ip, self.port), lambda *args, **kwargs: RequestHandler(self, *args, **kwargs)) as server:
            print(f"EL: {self.id} -  Starting elve listener: {self.ip}:{self.port}")
            try: 
                server.serve_forever()
            finally:
                server.server_close()

    def elf_writer(self):
        while True:
            self.sleep_time = random.randint(3,5) # Updating the sleeping time
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
            print(f'EW {self.id} - connecting to {port}:{port}')
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

