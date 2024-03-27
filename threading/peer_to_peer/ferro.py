from __future__ import print_function
from pysyncobj.batteries import ReplList, ReplLockManager, ReplCounter
from pysyncobj import SyncObj, SyncObjException, SyncObjConf, FAIL_REASON, replicated

import sys
import threading
import struct
import socketserver
import socket
import pickle
import time
from functools import partial

sys.path.append("../")
SANTA_PORT = 29800
LOCAL_HOST = "127.0.0.1"
NUM_ELVES = 6

class ElfSantaContacter(SyncObj):

    class RequestHandler(socketserver.StreamRequestHandler):
            def handle(self):
                print('ELFCONTACTER Recieved a message')
                identifier = self.request.recv(1).decode() # Recieving the identifier
                        
                if identifier == 'E': #Identifier is the Elves
                    
                    TCPNode_bytes = self.request.recv(1024)
                    TCPNode = pickle.loads(TCPNode_bytes)  # Deserialize bytes back into TCPNode


    def __init__(self, my_addr, partners):
        cfg = SyncObjConf(
            dynamicMembershipChange=True
        )
        super(ElfSantaContacter, self).__init__(my_addr, partners, conf=cfg)
        self._partners = partners


    def listen_santa(self):
        # Start server side
        with socketserver.ThreadingTCPServer(('localhost', 8888), self.RequestHandler) as server:
            print(f"Elf listener -  Starting elf listener: localhost:8888")
            try: 
                server.serve_forever()
            finally:
                server.server_close()



    def contact_santa(self):
        # Sent msg to Santa whom then msg's back here so that we can notify_all()
        try:
            print(
                f"ELF: {self.selfNode} -  Connecting to Santa at: "
                f"{LOCAL_HOST}:{SANTA_PORT}"
            )
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as conn_socket:

                conn_socket.connect((LOCAL_HOST, SANTA_PORT))

                identifier = "E"  # E for elves as identifier
                #node_bytes = pickle.dumps(self.selfNode)  # Serialize TCPNode to bytes
                buffer = bytearray()
                buffer.extend(identifier.encode())
                #buffer.extend(node_bytes)

                conn_socket.sendall(buffer)

        except ConnectionRefusedError:
            print(
                f"ELF: {self.selfNode} -  Couldn't conncect at: "
                f"{LOCAL_HOST}:{SANTA_PORT}"
            )



    def run(self):
        print(f"ELF: {self.selfNode} - Partners: {self._partners}")
        print(f"ELF: {self.selfNode} - Running ElfSantaContacter")

        while True:
            time.sleep(1)
            if self._getLeader() is None:
                print(f"SANTACONTACTERELF: {self.selfNode} - No leader")
                continue

            if self._isLeader():

                sub_threads = [
                    threading.Thread(target=self.listen_santa),
                    threading.Thread(target=self.contact_santa)
                ]

                for sub_thread in sub_threads:
                    sub_thread.start()

                for sub_thread in sub_threads:
                    sub_thread.join()
                break


class ElfWorker(SyncObj):
    def __init__(self, my_addr, partners, list, lockManager):
        super(ElfWorker, self).__init__(
            my_addr,
            partners,
            consumers=[list, lockManager],
            conf=SyncObjConf(dynamicMembershipChange=True,
                             commandsWaitLeader=True,
                             connectionTimeout=12,
                             ),
        )
        self._elvesWithProblems = list
        self._lock = lockManager
        self._memberOfCluster = True
        self._hasAppended = False
        self._connectedToMainCluster = True


    def onNodeRemoved(self, res, err, node):
        if err == FAIL_REASON.SUCCESS:
            print(f"ELF: {self.selfNode} - Removal - REQUEST SUCCESS: {node}")
 
    def onAppendComplete(self, result, error):
        print(
            f"ELF: {self.selfNode} - Append complete, error: {error}, result: {result}")

    def run(self):
        while True:

            if not self._connectedToMainCluster:
                continue

            time.sleep(0.5)

            if self._getLeader() is None:
                # Nodes without a leader should wait until one is elected
                # Could also be the case that this node is consulting Santa
                print(f"ELF: {self.selfNode} - No leader")
                continue

            #print(f"Elf{self.selfNode} has a list: {
            #      self._elvesWithProblems.rawData()}")
            #print(f"leader is: {self._getLeader()}")

            # If the list is full and the node is not in the list, remove nodes from the list
            if self._elvesWithProblems.count(self.selfNode) == 0 and len(self._elvesWithProblems.rawData()) > 0:

                node_partners = [p for p in self._elvesWithProblems.rawData()]

                # Remove nodes from the list
                for node in node_partners:
                    self.removeNodeFromCluster(
                        node,
                        callback=partial(
                            self.onNodeRemoved,
                            node=node
                        )
                    ) 

            # If the node is in the list destroy the process
            if self._elvesWithProblems.count(self.selfNode) == 1:
                self.destroy()
                self._connectedToMainCluster = False
                print(f"ELF: {self.selfNode} - kicked elf has this list: {self._elvesWithProblems.rawData()}")
                node_partners = [p for p in self._elvesWithProblems.rawData() if p != self.selfNode]

                if len(node_partners) > 1:
                    threads = []
                    # Create a thread for each partner that should contact Santa
                    for node in self._elvesWithProblems.rawData():
                        partners = [p for p in self._elvesWithProblems.rawData() if p != node]
                        thread = threading.Thread(target=ElfSantaContacter(node, partners).run)
                        threads.append(thread)

                    for thread in threads:
                        thread.start()
                    
                    for thread in threads:
                        thread.join()
                    
                   

            if self._isLeader():
                try:
                    if self._lock.tryAcquire("testLockName", sync=True):
                        if len(self._elvesWithProblems.rawData()) < 3 and self._elvesWithProblems.count(self.selfNode) == 0:

                            self._elvesWithProblems.append(self.selfNode,
                                                           callback=self.onAppendComplete)
                            
                            
# K                            break
                except:
                    print(f"ELF: {self.selfNode} - Couldn't acquire lock")
                finally:
                    if self._lock.isAcquired("testLockName"):
                        self._lock.release("testLockName")


if __name__ == "__main__":
    start_port = 3000
    ports = [start_port + i for i in range(NUM_ELVES)]

    threads = []

    for i, port in enumerate(ports):
        # Create a list of partners for each ElfWorker
        my_addr = "localhost:%d" % port
        partners = ["localhost:%d" % int(p) for p in ports if p != port]
        print(f"ELF: {my_addr} - Partners: {partners}")

        # Create a new ReplList and ReplLockManager data structures
        list = ReplList()
        lockManager = ReplLockManager(autoUnlockTime=75)

        # Create a new ElfWorker
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
