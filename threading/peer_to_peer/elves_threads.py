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
        if msg_type == MSG_TYPE.SANTA._value_:
            self.handle_santa_msg(payload)
        elif msg_type == MSG_TYPE.FEELER._value_:
            self.handle_feeler_msg(payload)
        elif msg_type == MSG_TYPE.ACKNOWLEDGEMENT._value_:
            self.handle_acknowledgement_msg(payload)
        elif msg_type == MSG_TYPE.READY_REQUEST._value_:
            self.handle_ready_request_msg(payload)
        elif msg_type == MSG_TYPE.READY_RESPONSE._value_:
            self.handle_ready_response_msg(payload)
        elif msg_type == MSG_TYPE.REJECT._value_:
            self.handle_reject_msg(payload)

    def handle_santa_msg(self, payload):
        pass

    def handle_feeler_msg(self, payload):
        def create_feeler_response_data(peer_triple, my_triple):
            if self.Elf.is_chain_root:
                return {
                    'type': MSG_TYPE.REJECT._value_,
                    'peer_id': self.Elf.id
                }
            else:
                return {
                    'type': MSG_TYPE.ACKNOWLEDGEMENT._value_,
                    'chain': [peer_triple, my_triple]
                }

        peer_id, peer_port, peer_sleep_time = payload['id'], payload['port'], payload['sleep_time']
        peer_triple = (peer_sleep_time, peer_id, peer_port)
        my_triple = (self.Elf.sleep_time, self.Elf.id ,self.Elf.port)
        print(f'ELF {self.Elf.id} - RECIEVED THE FEELER FROM ELF {peer_id}')

        with self.Elf.lock:
            data = create_feeler_response_data(peer_triple, my_triple)
        buffer = self.Elf.create_buffer(data)
        self.Elf.send_message(LOCAL_HOST, peer_port, buffer)


    def handle_acknowledgement_msg(self, payload):
        def extract_peer_triple(chain):
            peer_sleep_time = chain[1][0]
            peer_id = chain[1][1]
            peer_port = chain[1][2]
            return (peer_sleep_time, peer_id, peer_port)

        def update_chain(peer_triple, my_triple):
            if len(self.Elf.chain) < NUM_CHAIN:
                if peer_triple not in self.Elf.chain:
                    bisect.insort(self.Elf.chain, peer_triple)

                if my_triple not in self.Elf.chain: 
                    bisect.insort(self.Elf.chain, my_triple)

        def check_and_set_chain_root():
            first_elf_in_chain_id = self.Elf.chain[0][1]
            if len(self.Elf.chain) == NUM_CHAIN and first_elf_in_chain_id == self.Elf.id:
                self.Elf.is_chain_root = True
                print(f'Elf {self.Elf.id} - I am Groot') # Xd 
                print(f'ELF {self.Elf.id} - I ROOT OF THE CHAIN {self.Elf.chain}')
            else:
                self.Elf.is_chain_root = False

        def send_ready_request_to_chain():
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

        chain = payload['chain']
        peer_triple = extract_peer_triple(chain)
        my_triple = (self.Elf.sleep_time, self.Elf.id , self.Elf.port)

        with self.Elf.lock:
            update_chain(peer_triple, my_triple)
            check_and_set_chain_root()
            if self.Elf.is_chain_root:
                send_ready_request_to_chain()

    def handle_ready_request_msg(self, payload):
        def send_ready_response(peer_port):
            msg_type = MSG_TYPE.READY_RESPONSE._value_ 
            data = {
                'type': msg_type,
                'is_ready_to_join_chain': int(self.Elf.is_ready_to_join_chain),
                'peer_id': self.Elf.id
            }
            self.Elf.is_ready_to_join_chain = False
            buffer = self.Elf.create_buffer(data)
            self.Elf.send_message(LOCAL_HOST, peer_port, buffer)

        peer_port = payload['peer_port']

        with self.Elf.lock:
            send_ready_response(peer_port)

    def handle_ready_response_msg(self, payload):
        def handle_ready():
            self.Elf.ready_count += 1

        def handle_not_ready(peer_id):
            print(f'ELF {self.Elf.id} - Elf {peer_id} is not ready')
            # if the elf is not ready, clear the chain and start over
            self.Elf.chain = []
            self.Elf.is_chain_root = False
            self.Elf.ready_count = 0
            # TODO: Send message to the other elves to start over

        def contact_santa():
            # TODO: Contact Santa 
            print(f'Elf {self.Elf.id} - Is contacting Santa')

        ready = payload['is_ready_to_join_chain']
        peer_id = payload['peer_id']

        with self.Elf.lock:
            if not ready:
                handle_not_ready(peer_id)
            else:
                handle_ready()

            if self.Elf.ready_count == NUM_CHAIN - 1: # If the other elves in the chain are ready
                contact_santa()

    def handle_reject_msg(self, payload):
        peer_id = payload['peer_id']
        print(f'ELF {self.Elf.id} - GOT REJECTED by ELF {peer_id}')
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
            self.sleep_time =  random.randint(3,5) # Updating the sleeping time
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
            #with self.condition:
            #    self.condition.wait()

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

