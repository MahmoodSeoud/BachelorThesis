import socket
import socketserver
import struct
import threading
import time
import random
from enum import Enum

class MSG_TYPE(Enum):
    SANTA = 1
    FEELER = 2
    ACKNOWLEDGEMENT = 3
    ERROR = 4
    JOIN_CHAIN = 5

NUM_ELVES = 3
LOCAL_HOST = "127.0.0.1"
SANTA_PORT = 29800

class RequestHandler(socketserver.StreamRequestHandler):
    def __init__(self, Elf, *args, **kwargs):
        self.Elf = Elf
        super().__init__(*args, **kwargs)

    def handle(self):
        
        # Receive the message type
        msg_type_data = self.request.recv(4)
        msg_type = struct.unpack('!I', msg_type_data)[0]

        if msg_type == MSG_TYPE.SANTA._value_: # Handle a string message from Santa
            # Receive the length of the string (4 bytes for an unsigned integer)
            request_header = self.request.recv(4)
            request_length = struct.unpack('!I', request_header)[0]
            payload = self.request.recv(request_length)

            print(f"Elves - Recieved message: {payload.decode('ascii')}")
            print('--------------------------') # Print line to indicicate new cycle

        elif msg_type == MSG_TYPE.FEELER._value_:  # Handle a tuple message from other Elf
            request_header = self.request.recv(12)
            port = struct.unpack('!I', request_header)[0]

            msg_type = MSG_TYPE.ACKNOWLEDGEMENT._value_ 
            buffer = bytearray()
            buffer.extend(struct.pack('!I', msg_type))
            with self.Elf.lock:
                buffer.extend(struct.pack('!4I', 
                                            self.Elf.id, 
                                            self.Elf.sleep_time,
                                            int(self.Elf.is_chain_root), 
                                            len(self.Elf.chain)))
            
            self.Elf.send_message(LOCAL_HOST, port, buffer)

        elif msg_type == MSG_TYPE.ACKNOWLEDGEMENT._value_: # Handle the case of acceptance
            request_header = self.request.recv(16)
            id, sleep_time, he_was_root, chain_length = struct.unpack('!4I', request_header)

            with self.Elf.lock:
                if not self.Elf.is_chain_member:
                    if he_was_root and chain_length < NUM_ELVES:
                        self.Elf.is_chain_member = True

                        # Attempt to join the chain
                        msg_type = MSG_TYPE.JOIN_CHAIN._value_ 

                        buffer = bytearray()
                        buffer.extend(struct.pack('!I', msg_type))
                        buffer.extend(struct.pack('!2I', self.Elf.id, self.Elf.sleep_time))
                    else:
                        # If none is root or there is not enough space for me, create my own
                        self.Elf.is_chain_root = True                      
                        self.Elf.is_chain_member = True                      

                        self.Elf.chain.append((self.Elf.id, self.Elf.sleep_time))
                    
                    print(f'Elf {self.Elf.id} - I think the chain is {self.Elf.chain}')

        elif msg_type == MSG_TYPE.JOIN_CHAIN._value_:
            request_header = self.request.recv(8)
            id, sleep_time = struct.unpack('!2I', request_header)[0]

            with self.Elf.lock:
                self.Elf.chain.append((id, sleep_time))

            print(f'Elf{self.Elf.id} - believe the chain is {self.Elf.chain}')


        elif msg_type == MSG_TYPE.ERROR._value_: # Handle the case of reject
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
            if not self.is_chain_root:
                msg_type = MSG_TYPE.FEELER._value_

                buffer = bytearray()
                buffer.extend(struct.pack('!I', msg_type))
                buffer.extend(struct.pack('!I', self.port))

                # Msg all the other elves about presence of chain root
                for peer_port in self.peer_ports:
                    if peer_port != self.port:
                        self.send_message(LOCAL_HOST, peer_port, buffer)

            # Waiting for all the threads to sync
            with self.condition:
                self.condition.wait()

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

