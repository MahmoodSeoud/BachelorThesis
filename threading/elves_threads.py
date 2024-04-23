from __future__ import print_function
from pysyncobj import SyncObj, SyncObjConf, FAIL_REASON, replicated
from pysyncobj.batteries import ReplLockManager, ReplSet

import sys
import os
import threading
import socketserver
import socket
import time
import struct
from functools import partial

sys.path.append("../")
LOCAL_HOST = "127.0.0.1"

CHAIN_LEADER_PORT = 8888
SANTA_PORT = 29800

NUM_ELVES = 10


class ElfContacter():

    def __init__(self, sender, local_chain_members=None):
        self.sender = sender
        self.local_chain_members = local_chain_members

    # Class for handling the connection between the elves and Santa
    class RequestHandler(socketserver.StreamRequestHandler):
        def handle(self):
            data = self.request.recv(1024)
            message = data.decode('utf-8')
            print(f"[CHAIN CLUSTER] Received a message from Santa: {message}")

    def listener(self, host, port):
        with socketserver.ThreadingTCPServer((host, port), self.RequestHandler) as server:
            print( f"[{self.sender}] - Starting listener: ({host}:{port})")
            try:
                server.handle_request()  # Server will handle the request from Santa and then close
            finally:
                server.server_close()

    def contact_santa(self, sender, host, port, chain):
        chain_as_list = list(chain)
        chain_as_list.append(sender)

        buffer = bytearray()
        buffer.extend('E'.encode())
        buffer.extend(struct.pack('!3I', chain_as_list[0], chain_as_list[1], chain_as_list[2]))
        send_message(sender, host, port, buffer)

    def start_threads(self):
        sub_threads1 = [
            threading.Thread(target=self.listener, args=(
                LOCAL_HOST, self.sender)),
            threading.Thread(target=self.contact_santa,
                             args=(self.sender, LOCAL_HOST, SANTA_PORT, self.local_chain_members )),
        ]

        for sub_thread in sub_threads1:
            sub_thread.start()

        for sub_thread in sub_threads1:
            sub_thread.join()

    def run(self):
        self.start_threads()


class ElfWorker(SyncObj):
    def __init__(self, nodeAddr, otherNodeAddrs, consumers):
        self._is_in_chain = False
        #self.__chain = set()
        #self.lockManager = consumers[0]
        self.__local_chain_members = None

        super(ElfWorker, self).__init__(
            nodeAddr,
            otherNodeAddrs,
            consumers=consumers,
            conf=SyncObjConf(
                dynamicMembershipChange=True,
                connectionRetryTime=10.0,
                logCompactionSplit=True
            ),
        )

                   
def startElfContacter(port, chainMembers=None):
    ElfContacter(port, chainMembers).run()

def startElfListener(port):
    ElfContacter(port).listener(LOCAL_HOST, port)

def onNodeAdded(result, error, node, cluster):
    if error == FAIL_REASON.SUCCESS:
        print(
            f"ADDED - REQUEST [SUCCESS]: {node} - CLUSTER: {cluster}")


def send_message(sender, host, port, buffer):
    try:
        print(f'[{sender}] connecting to {host}:{port}')
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as conn_socket:
            conn_socket.connect((host, port))
            conn_socket.sendall(buffer)

    except ConnectionRefusedError:
        print(f"{sender} Couldn't connect to " f"{host}:{port}.")

def handleFerro(elf_worker, extraPort, localChainMembers=None):

    while True:
        time.sleep(0.5)

        # Check if there's a leader, if not, continue waiting
        leader = elf_worker._getLeader()
        if leader is None:
            continue
        try:
            # Attempt to acquire the lock
            if lockManager.tryAcquire("chainLock", sync=True):
                print("elf_worker acquired the loc",elf_worker.selfNode)

                # Check if the chain is eligible for modification
                if len(chain.rawData()) < 3 and elf_worker.selfNode not in chain.rawData():
                    # Add elf_worker to the chain if it's not full and elf_worker is not already in it
                    chain.add(extraPort, callback=partial(
                        onNodeAdded, node=extraPort, cluster="chain"))
                    elf_worker._is_in_chain = True
                    

                    # Plus one because the the effect might not be immediate
                    if len(chain.rawData()) + 1 == 3:
                        localChainMembers = chain.rawData()
                        chain.clear()

                # Release the lock
                lockManager.release("chainLock")
                print("elf_worker released the loc",elf_worker.selfNode)

                if elf_worker._is_in_chain:

                    if localChainMembers is None:
                        startElfListener(extraPort)
                        elf_worker._is_in_chain = False
                    else:
                        startElfContacter(extraPort, localChainMembers)
                        localChainMembers = None   

                        elf_worker._is_in_chain = False

        except Exception as e:
            print(f"Exception: {e}")
        finally:
            if lockManager.isAcquired("chainLock"):
               lockManager.release("chainLock")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: %s [-t] self_port partner1_port partner2_port ...' % sys.argv[0])
        sys.exit(-1)

    if (sys.argv[1] == '-t'):
        print('Running in threading mode')
        start_port = 10000
        # +1 for the leader/manager
        ports = [start_port + i*1000 for i in range(NUM_ELVES + 1)]

        threads = []
        lockManager = ReplLockManager(autoUnlockTime=75.0)

        for i, port in enumerate(ports):
            # Create a list of otherNodeAddrs for each ElfWorker
            nodeAddr = f"{LOCAL_HOST}:{port}"
            otherNodeAddrs = [f"{LOCAL_HOST}:{p}" for p in ports if p != port]
            # Create a new ReplList and ReplLockManager data structures
            elf_worker = ElfWorker(nodeAddr, otherNodeAddrs, consumers=[lockManager, chain], extraPort=port+1)
            
            # Create a new thread for each ElfWorker and add it to the list
            thread = threading.Thread(target=handleFerro, args=(elf_worker, port+1) , daemon=True)
            threads.append(thread)

        # Start all the threads
        for thread in threads:
            thread.start()

        # Join all the threads
        for thread in threads:
            thread.join()


    else:
        nodeAddr = f"{LOCAL_HOST}:{sys.argv[1]}"
        otherNodeAddrs = [f"{LOCAL_HOST}:{p}" for p in sys.argv[2:]]

        port = int(sys.argv[1])
        #dumpFiles = [getNextDumpFile(port)]
        # Create a new ReplList and ReplLockManager data structures
        lockManager = ReplLockManager(autoUnlockTime=75.0)
        chain = ReplSet()
        elf_worker = ElfWorker(nodeAddr, otherNodeAddrs, consumers=[lockManager, chain ])
        handleFerro(elf_worker, port+1)








