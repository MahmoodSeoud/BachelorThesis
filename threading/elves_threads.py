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
    def __init__(self, nodeAddr, otherNodeAddrs, consumers, extraPort):
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

        self._is_in_chain = False
        self.lockManager = consumers[0]
        self.chain = consumers[1]
        self.__local_chain_members = None
        self.__extraPort = extraPort  

    def run(self):
        while True:
            time.sleep(0.5)

            # Check if there's a leader, if not, continue waiting
            leader = self._getLeader()
            if leader is None:
                continue
            try:
                # Attempt to acquire the lock
                if self.lockManager.tryAcquire("chainLock", sync=True):

                    # Check if the chain is eligible for modification
                    if len(chain.rawData()) < 3 and self.selfNode not in chain.rawData():
                        # Add self to the chain if it's not full and self is not already in it
                        self.chain.add(self.__extraPort, callback=partial(
                            onNodeAdded, node=self.__extraPort, cluster="chain"))
                        self._is_in_chain = True
                        

                        # Plus one because the the effect might not be immediate
                        if len(self.chain.rawData()) + 1 == 3:
                            self.__local_chain_members = self.chain.rawData()   
                            self.chain.clear()

                    # Release the lock
                    self.lockManager.release("chainLock")

                    if self._is_in_chain:

                        if self.__local_chain_members is None:
                            startElfListener(self.__extraPort)
                            self._is_in_chain = False
                        else:
                            startElfContacter(self.__extraPort, self.__local_chain_members)
                            self.__local_chain_members = None   
                            self._is_in_chain = False

            except Exception as e:
                print(f"Exception: {e}")
            finally:
                if self.lockManager.isAcquired("chainLock"):
                    self.lockManager.release("chainLock")

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

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print('Usage: %s [-t] self_port partner1_port partner2_port ...' % sys.argv[0])
        sys.exit(-1)
 
    nodeAddr = f"{LOCAL_HOST}:{sys.argv[1]}"
    otherNodeAddrs = [f"{LOCAL_HOST}:{p}" for p in sys.argv[2:]]

    port = int(sys.argv[1])
    # Create a new ReplList and ReplLockManager data structures

    lockManager = ReplLockManager(autoUnlockTime=75.0)
    chain = ReplSet()
    elf_worker = ElfWorker(nodeAddr, otherNodeAddrs, consumers=[lockManager, chain], extraPort=port+1)
    elf_worker.run()







