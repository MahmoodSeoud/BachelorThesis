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

    def onAppend(self, res, err, node):
        # Release the lock and connect to the other elves
        print('on appned \n list:', node, "\n result", res, "\n error:", err)

        """   if (err == FAIL_REASON.REQUEST_DENIED):
            print('Failed to append node \n list:', node,
                  "\n result", res, "\n error:", err)
        else:
            self._lock.release('testLockName', callback=partial(
                self.onRelease, node=node)) """

    def onRelease(self, res, err, node):
        # Close the connection to the other elves and make his own cluster
        if (err == FAIL_REASON.REQUEST_DENIED):
            print('Failed to release lock \n list:', node,
                  "\n result", res, "\n error:", err)
        else:
            self.destroy()
            self._destroyed = True
            elf_santa_Contacter = ElfSantaContacter(
                node, self._elvesWithProblems.rawData())
            elf_santa_Contacter.run()

    def run(self):
        while not self._destroyed:
            time.sleep(0.5)
        
            if self._getLeader() is None:
                continue

            if self._lock.tryAcquire('testLockName', sync=True):
                print(f"Elf: {self.getStatus()['self']} acquired lock")
                self_node = self.getStatus()['self']
                print(self._elvesWithProblems.rawData())
                if self_node not in self._elvesWithProblems.rawData() and len(self._elvesWithProblems.rawData()) < 3:
                    self._elvesWithProblems.append(self_node, callback=partial(self.onAppend, node=self_node))

                self._lock.release('testLockName')
                print(f"Elf: {self.getStatus()['self']} released lock")
                    #self._lock.release('testLockName', callback=partial( self.onRelease, node=self.getStatus()['self']))


if __name__ == '__main__':
    start_port = 3000
    ports = [start_port + i for i in range(NUM_ELVES)]

    threads = []

    for i, port in enumerate(ports):
        my_addr = 'localhost:%d' % port
        partners = ['localhost:%d' % int(p) for p in ports if p != port]
        print(f"ELF: {my_addr} - Partners: {partners}")

        list = ReplList()
        lockManager = ReplLockManager(autoUnlockTime=75, selfID='testLockName')
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