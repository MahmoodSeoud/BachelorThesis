#!/usr/bin/env python
from __future__ import print_function
from pysyncobj.batteries import ReplList, ReplLockManager, ReplCounter
from pysyncobj import SyncObj, SyncObjException, SyncObjConf, FAIL_REASON

import sys
import struct
import socket
import pickle
import time
from functools import partial
sys.path.append("../")
SANTA_PORT = 29800
LOCAL_HOST = "127.0.0.1"


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
        if (err == FAIL_REASON.REQUEST_DENIED):
            print('Failed to append node \n list:', node,
                  "\n result", res, "\n error:", err)
        else:
            self._lock.release('testLockName', callback=partial(
                self.onRelease, node=node))

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

            if self.getStatus()['self'] is None:
                continue

            try:
                if self._lock.tryAcquire('testLockName', sync=True):
                    self_node = self.getStatus()['self']
                    if self_node not in self._elvesWithProblems.rawData() and len(self._elvesWithProblems.rawData()) < 3:
                        self._elvesWithProblems.append(self_node, callback=partial(
                            self.onAppend, node=self_node))
                print(f"Elf: {self.getStatus()['self']} list: {self._elvesWithProblems.rawData()}")
            except:
                print(f"Failed to acquire lock")


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Usage: %s self_port partner1_port partner2_port ...' %
              sys.argv[0])
        sys.exit(-1)

    port = 'localhost:%d' % int(sys.argv[1])
    partners = ['localhost:%d' % int(p) for p in sys.argv[2:]]

    counter = ReplCounter()
    list = ReplList()
    lockManager = ReplLockManager(autoUnlockTime=10, selfID='testLockName')

    elf_worker = ElfWorker(port, partners, list, lockManager)
    elf_worker.run()
