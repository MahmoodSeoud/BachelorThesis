#!/usr/bin/env python
from __future__ import print_function
from pysyncobj.batteries import ReplList, ReplLockManager, ReplCounter
from pysyncobj import SyncObj, SyncObjException, SyncObjConf, FAIL_REASON

import sys
import threading
import struct
import socket
import pickle
import time
from functools import partial
sys.path.append("../")
SANTA_PORT = 29800
LOCAL_HOST = "127.0.0.1"
NUM_ELVES = 4


class ElfSantaContacter(SyncObj):
    def __init__(self, my_addr, partners):
        super(ElfSantaContacter, self).__init__(my_addr, partners,
                                                conf=SyncObjConf(dynamicMembershipChange=True))
        self._partners = partners

    def contact_santa(self):
        # Sent msg to Santa whom then msg's back here so that we can notify_all()
        try:
            print(
                f"ELF: {self.getStatus()['self']} -  Connecting to Santa at: " f"{LOCAL_HOST}:{SANTA_PORT}")
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as conn_socket:

                conn_socket.connect((LOCAL_HOST, SANTA_PORT))

                identifier = 'E'  # E for elves as identifier
                node = self.getStatus()['self']
                node_bytes = pickle.dumps(node)  # Serialize TCPNode to bytes

                buffer = bytearray()
                buffer.extend(identifier.encode())
                buffer.extend(node_bytes)

                conn_socket.sendall(buffer)

        except ConnectionRefusedError:
            print(
                f"ELF: {self.getStatus()['self']} -  Couldn't conncect at: " f"{LOCAL_HOST}:{SANTA_PORT}")

    def run(self):
        print(f"ELF: {self.getStatus()['self']} - Partners: {self._partners}")
        print(f"ELF: {self.getStatus()['self']} - Running ElfSantaContacter")


class ElfWorker(SyncObj):
    def __init__(self, my_addr, partners, list, lockManager):
        super(ElfWorker, self).__init__(my_addr,
                                        partners,
                                        consumers=[list, lockManager],
                                        conf=SyncObjConf(
                                            dynamicMembershipChange=True)
                                        )
        self._elvesWithProblems = list
        self._lock = lockManager
        self._destroyed = False
        self._node = self.getStatus()['self']

    def run(self):
        while not self._destroyed:
            time.sleep(0.5)
        
            if self._getLeader() is None:
                continue

            print(f'Elf{self._node} has a list: {self._elvesWithProblems.rawData()}')

            # If chain is full, destroy the process to form his own connection
            if self._node in self._elvesWithProblems.rawData() and len(self._elvesWithProblems.rawData()) == 3:
                self.destroy()
                self._lock.destroy()
                self._destroyed = True # Set the flag to True to break the loop
                node_partners = [p for p in self._elvesWithProblems.rawData() if p != self._node]
                elf = ElfSantaContacter(self._node, node_partners)
                elf.run()
                continue
            
            if self._lock.tryAcquire('testLockName', sync=True):
                if self._node not in self._elvesWithProblems.rawData() and len(self._elvesWithProblems.rawData()) < 3:
                    self._elvesWithProblems.append(self._node)

                self._lock.release('testLockName')

if __name__ == '__main__':
    start_port = 3000
    ports = [start_port + i for i in range(NUM_ELVES)]

    threads = []

    for i, port in enumerate(ports):
        my_addr = 'localhost:%d' % port
        partners = ['localhost:%d' % int(p) for p in ports if p != port]
        print(f"ELF: {my_addr} - Partners: {partners}")

        list = ReplList()
        lockManager = ReplLockManager(autoUnlockTime=75)
        elf_worker = ElfWorker(my_addr, partners, list, lockManager)

        # Create a new thread for each ElfWorker and add it to the list
        thread = threading.Thread(target=elf_worker.run, daemon=True)
        threads.append(thread)

    # Start all the threads
    for thread in threads:
        thread.start()

    # Join all the threads
    for thread in threads:
        thread.join()