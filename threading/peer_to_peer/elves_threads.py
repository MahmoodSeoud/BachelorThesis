import socket
import socketserver
import threading
import time
import random
import bisect
import json
from enum import Enum

class State(Enum):
    SANTA = 1
    FEELER = 2
    ACKNOWLEDGEMENT = 3
    REJECT = 4
    READY_REQUEST = 5
    READY_RESPONSE = 6
    START_OVER = 7
    

NUM_ELVES = 4
NUM_CHAIN = 3
LOCAL_HOST = "127.0.0.1"
SANTA_PORT = 29800

class RequestHandler(socketserver.StreamRequestHandler):
    def __init__(self, elf, *args, **kwargs):
        self.elf = elf
        self.state_handlers = {
            State.SANTA: self.handle_santa_msg,
            State.FEELER: self.handle_feeler_msg,
            State.ACKNOWLEDGEMENT: self.handle_acknowledgement_msg,
            State.READY_REQUEST: self.handle_ready_request_msg,
            State.READY_RESPONSE: self.handle_ready_response_msg,
            State.REJECT: self.handle_reject_msg,
            State.START_OVER: self.handle_start_over_msg,
        }
        self.current_state = None
        super().__init__(*args, **kwargs)

    def handle(self):
        data_bytes = self.request.recv(1024)
        payload = json.loads(data_bytes.decode('utf-8'))
        msg_type = payload['type']
        self.change_state(State(msg_type), payload)

    def change_state(self, new_state, payload):
        handler = self.state_handlers.get(new_state)
        if handler:
            self.current_state = new_state
            handler(payload)

    def handle_santa_msg(self, payload):
        pass

    def handle_feeler_msg(self, payload):
        def create_feeler_response_data(peer_triple, my_triple, peer_is_chain_root):
            if peer_is_chain_root: # If peer is chain root, reject the request
                return {
                    'type': State.REJECT._value_,
                    'peer_id': peer_triple[1]
                }
            else:
                return {
                    'type': State.ACKNOWLEDGEMENT._value_,
                    'chain': [peer_triple, my_triple]
                }

        peer_id, peer_port, peer_sleep_time = payload['id'], payload['port'], payload['sleep_time']
        peer_is_chain_root = payload['peer_is_chain_root']
        peer_triple = (peer_sleep_time, peer_id, peer_port)
        my_triple = (self.elf.sleep_time, self.elf.id ,self.elf.port)
        print(f'ELF {self.elf.id} - RECIEVED THE FEELER FROM ELF {peer_id}')

        with self.elf.lock:
            data = create_feeler_response_data(peer_triple, my_triple, peer_is_chain_root)
        buffer = self.elf.create_buffer(data)
        self.elf.send_message(LOCAL_HOST, peer_port, buffer)


    def handle_acknowledgement_msg(self, payload):
        
        def extract_peer_triple(chain):
            peer_sleep_time = chain[1][0]
            peer_id = chain[1][1]
            peer_port = chain[1][2]
            return (peer_sleep_time, peer_id, peer_port)

        def update_chain(peer_triple, my_triple):
            if len(self.elf.chain) < NUM_CHAIN:
                if peer_triple not in self.elf.chain:
                    bisect.insort(self.elf.chain, peer_triple)

                if my_triple not in self.elf.chain: 
                    bisect.insort(self.elf.chain, my_triple)

        def send_ready_request_to_chain():
            data = {
                'type': State.READY_REQUEST._value_ ,
                'peer_port': self.elf.port
            }
            buffer = self.elf.create_buffer(data)
            print(f'ELF {self.elf.id} - SENDING READY REQUEST TO CHAIN {self.elf.chain}')
            for elf in self.elf.chain:
                peer_port = elf[2] #port
                if peer_port != self.elf.port: # Send to all the other elves if they are
                    self.elf.send_message(LOCAL_HOST, peer_port, buffer)

        chain = payload['chain']
        peer_triple = extract_peer_triple(chain)
        my_triple = (self.elf.sleep_time, self.elf.id , self.elf.port)
        print(f'ELF {self.elf.id} - RECIEVED THE ACKNOWLEDGEMENT FROM ELF {peer_triple[1]}')

        with self.elf.lock:
            update_chain(peer_triple, my_triple)
            first_elf_in_chain_id = self.elf.chain[0][1]
            if self.elf.id == 4:
                print(f'ELF {self.elf.id} - CHAIN {self.elf.chain}')
                print(f'ELF {self.elf.id} - FIRST ELF IN CHAIN {first_elf_in_chain_id}')
            if not self.elf.is_chain_root and len(self.elf.chain) == NUM_CHAIN and first_elf_in_chain_id == self.elf.id:
                self.elf.is_chain_root = True
                print(f'elf {self.elf.id} - I am Groot') # Xd 
                send_ready_request_to_chain()

    def handle_ready_request_msg(self, payload):

        def send_ready_response(peer_port):
            data = {
                'type': State.READY_RESPONSE._value_,
                'is_ready_to_join_chain': int(self.elf.is_ready_to_join_chain),
                'peer_id': self.elf.id,
                'peer_port': self.elf.port
            }
            self.elf.is_ready_to_join_chain = False
            buffer = self.elf.create_buffer(data)
            self.elf.send_message(LOCAL_HOST, peer_port, buffer)

        peer_port = payload['peer_port']

        with self.elf.lock:
            send_ready_response(peer_port)

    def handle_ready_response_msg(self, payload):
        def handle_ready():
            self.elf.ready_count += 1

        def handle_not_ready(peer_id, peer_port):
            print(f'ELF {self.elf.id} - ELF {peer_id} is not ready')
            # if the elf is not ready, clear the chain and start over
            self.elf.chain = []
            self.elf.is_chain_root = False
            self.elf.ready_count = 0
            # TODO: Send message to the other elves to start over
            data = {
                'type': State.START_OVER._value_,
            }
            buffer = self.elf.create_buffer(data)
            self.elf.send_message(LOCAL_HOST, peer_port, buffer)

        def contact_santa():
            # TODO: Contact Santa 
            print(f'ELF{self.elf.id} - CONFIRMED CHAIN {self.elf.chain}')
            print(f'elf {self.elf.id} - Is contacting Santa')

        ready = payload['is_ready_to_join_chain']
        peer_id = payload['peer_id']
        peer_port = payload['peer_port']

        with self.elf.lock:
            if not ready:
                handle_not_ready(peer_id, peer_port)
            else:
                handle_ready()

            if self.elf.ready_count == NUM_CHAIN - 1: # If the other elves in the chain are ready
                contact_santa()

    def handle_reject_msg(self, payload):
        peer_id = payload['peer_id']
        print(f'ELF {self.elf.id} - DONT WANT MORE ROOTS: ELF {peer_id}')

    def handle_start_over_msg(self):
        print(f'ELF {self.elf.id} - STARTING OVER')
        self.elf.is_ready_to_join_chain = True
        self.elf.is_chain_root = False
        self.elf.chain = []
        self.elf.ready_count = 0

        with self.elf.condition:
            self.elf.condition.notify() # Notify the writer thread to start over


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
        self.is_ready_to_join_chain = True
        self.ready_count = 0
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
            self.sleep_time =  self.find_sleeping_time_testing()#random.randint(3,5) # Updating the sleeping time
            time.sleep(self.sleep_time)  # Simulate elf working
            print(f'Elf {self.id} has problems after {self.sleep_time} seconds')

            # If the elf is not forming a group, initiate group formation
            # Send message to peers about group formation
            data = {
                'type': State.FEELER._value_,
                'id': self.id,
                'sleep_time': self.sleep_time,
                'port': self.port,
                'peer_is_chain_root': int(self.is_chain_root),
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
