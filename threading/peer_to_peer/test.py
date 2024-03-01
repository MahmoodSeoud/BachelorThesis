import threading
import time
import random
import socket
import struct

# Constants
NUM_ELFS = 10  # Number of elves
ELF_PORTS = range(5000, 5000 + NUM_ELFS)  # Port numbers for elves

class Elf(threading.Thread):
    def __init__(self, elf_id, previous_elf=None, next_elf=None):
        super().__init__()
        self.elf_id = elf_id
        self.previous_elf = previous_elf
        self.next_elf = next_elf

    def run(self):
        # Simulate elf working
        while True:
            sleep_time = random.randint(3, 5)
            time.sleep(sleep_time)
            print(f'Elf {self.elf_id} has problems after {sleep_time} seconds')

            # If the elf has no next elf, it's the latest elf in the chain
            if self.next_elf is None:
                print(f'Elf {self.elf_id} is the latest elf in the chain')
                break

            # Send message to the next elf in the chain
            print(f'Elf {self.elf_id} is sending a message to Elf {self.next_elf.elf_id}')
            self.send_message_to_next_elf()

    def send_message_to_next_elf(self):
        # Create a message to send to the next elf
        msg_type = 1  # Assume message type 1 for now
        message = f'Message from Elf {self.elf_id} to Elf {self.next_elf.elf_id}'

        # Send the message to the next elf
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
            client_socket.connect(('localhost', self.next_elf.port))
            client_socket.sendall(struct.pack('!I', msg_type))  # Send message type
            client_socket.sendall(struct.pack('!I', len(message)))  # Send message length
            client_socket.sendall(message.encode())  # Send message payload

def create_elves():
    elves = []

    # Create elves
    for i in range(NUM_ELFS):
        elf = Elf(i)
        elves.append(elf)

    # Connect elves in a chain
    for i in range(NUM_ELFS):
        if i > 0:
            elves[i].previous_elf = elves[i - 1]
        if i < NUM_ELFS - 1:
            elves[i].next_elf = elves[i + 1]

    return elves

if __name__ == '__main__':
    # Create elves and start them
    elves = create_elves()
    for elf in elves:
        elf.start()

    # Wait for all elves to finish
    for elf in elves:
        elf.join()

