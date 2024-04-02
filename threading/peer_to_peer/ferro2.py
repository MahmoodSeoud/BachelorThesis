from __future__ import print_function
from queue import Queue
from pysyncobj import SyncObj, SyncObjException, SyncObjConf, FAIL_REASON, replicated
from pysyncobj.batteries import ReplLockManager

import sys
import threading
import socketserver
import socket
import time
from functools import partial

sys.path.append("../")
LOCAL_HOST = "127.0.0.1"

CHAIN_LEADER_PORT = 8888
SANTA_PORT = 29800

NUM_ELVES = 10

class ElfContacter():

    def __init__(self, sender):
        self.sender = sender

    # Class for handling the connection between the elves and Santa
    class RequestHandler(socketserver.StreamRequestHandler):
        def handle(self):
            data = self.request.recv(1024)
            message = data.decode('utf-8')
            print(f"[CHAIN CLUSTER] Received a message from Santa: {message}")


    # Function for the elf to listen for Santa
    def listener(self, host, port):
        with socketserver.ThreadingTCPServer((host, port), self.RequestHandler) as server:
            print(
                f"[CHAIN CLUSTER] - Starting listener: ({host}:{port})")
            try:
                server.handle_request()  # Server will handle the request from Santa and then close
            finally:
                server.server_close()
                print(f"Closed server at: {host}:{port}")

    def contact_entity(self, sender, host, port, identifier):
        # print(f"[CHAIN CLUSTER] - {self.selfNode} - Connecting to entity at: {host}:{port}")
        buffer = bytearray()
        buffer.extend(identifier.encode())
        send_message(sender, host, port, buffer)

    def start_threads(self):
        sub_threads1 = [
            threading.Thread(target=self.listener, args=(
                LOCAL_HOST, CHAIN_LEADER_PORT)),
            threading.Thread(target=self.contact_entity,
                             args=(self.sender, LOCAL_HOST, SANTA_PORT, 'E')),
        ]

        for sub_thread in sub_threads1:
            sub_thread.start()

        for sub_thread in sub_threads1:
            sub_thread.join()


    def run(self):
        print(f"ELF: - Running ElfContacter")
        self.start_threads()


class ElfWorker(SyncObj):
    def __init__(self, nodeAddr, otherNodeAddrs, consumers):
        super(ElfWorker, self).__init__(
            nodeAddr,
            otherNodeAddrs,
            consumers=consumers,
            conf=SyncObjConf(
                dynamicMembershipChange=True,
                # commandsWaitLeader=True,
                connectionRetryTime=5
            ),
        )
        # self.node_chain, self.queue, self.lock_manager = consumers
        self.chain_is_out = False
        self.first_time = True
        self.isAlive = True
        self.server = None
        self.__chain = set()
        self.__queue = Queue()
        self.lock_manager = consumers[0]
        self.__consumers = consumers
        self.__unlucky_node = None

    @replicated
    def addNodeToChain(self, node):
        self.__chain.add(node)
        return self.__chain

    @replicated
    def clearChain(self):
        self.__chain.clear()

    @replicated
    def enqueue(self, element):
        return self.__queue.put(element)

    @replicated
    def set_chain_is_out(self, value):
        self.chain_is_out = value
        return self.chain_is_out
    
    @replicated
    def set_unlucky_node(self, node):
        self.__unlucky_node = node
        return self.__unlucky_node

    def dequeue(self):
        return self.__queue.get()

    def getQueueSize(self):
        return self.__queue.qsize()

    def getChain(self):
        return self.__chain

    def get_chain_is_out(self):
        return self.chain_is_out

    def get_unlucky_node(self):
        return self.__unlucky_node

    class RequestHandler(socketserver.StreamRequestHandler):
        def __init__(self, *args, server=None, **kwargs):
            self.server = server
            super().__init__(*args, **kwargs)

        def handle(self):
            print("[MAIN CLUSTER] Recieved a message from a chain cluster")
            self.server.contact_chain_cluster_leader()
            time.sleep(1)

            for node in self.server.node_chain.rawData():
                self.server.addNodeToCluster(
                    node, callback=partial(onNodeAdded, node=node, cluster="main"))

            self.server.set_chain_is_out(False)
            self.server.node_chain.clear()

    def run(self):
        while True:
            time.sleep(0.5)

            if self._getLeader() is None:
                # Nodes without a leader should wait until one is elected
                continue

            if self.lock_manager.tryAcquire("elfContactLock", sync=True):
                if self.selfNode == self.get_unlucky_node():
                        ElfContacter(self.selfNode).run()
                        print("ElfContater done")
                        self.set_chain_is_out(False)
                        self.set_unlucky_node(None)
                self.lock_manager.release("elfContactLock")

            if self.getQueueSize() > 0 and self.get_chain_is_out() is False:
                self.set_chain_is_out(True)

                chain = self.dequeue()
                unluckyNode = list(chain)[0] # Get the first node in the chain
                print("unLucky",unluckyNode)
                print("Chain",list(chain))
                self.set_unlucky_node(unluckyNode)

                self.clearChain()

                while self.selfNode in chain and self.selfNode != self.get_unlucky_node():
                    time.sleep(0.5)

            try:
                if self.lock_manager.tryAcquire("chainLock", sync=True):
                    if len(self.getChain()) < 3:
                        self.addNodeToChain(self.selfNode, callback=partial(
                            onNodeAdded, node=self.selfNode, cluster="chain"))
                        
                    elif len(self.getChain()) == 3: 
                            self.enqueue(self.getChain())
            except Exception as e:
                print(f"ELF: {self.selfNode} - Could not acquire lock: {e}")
            finally:
                if self.lock_manager.isAcquired("chainLock"):
                    self.lock_manager.release("chainLock")


def onAdd(res, err, cnt):
    print('onAdd %d:' % cnt, res, err)


def onAppend(result, error, node):
    if error == FAIL_REASON.SUCCESS:
        print(f"APPEND - REQUEST [SUCCESS]: {node}")


def onNodeAdded(result, error, node, cluster):
    if error == FAIL_REASON.SUCCESS:
        print(f"ADDED - REQUEST [SUCCESS]: {node} - CLUSTER: {cluster}")


def onNodeRemoved(result, error, node, cluster):
    if error == FAIL_REASON.SUCCESS:
        print(f"REMOVED - REQUEST [SUCCESS]: {node} - CLUSTER: {cluster}")


def send_message(sender, host, port, buffer):
    try:
        print(f'{sender} connecting to {host}:{port}')
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as conn_socket:
            conn_socket.connect((host, port))
            conn_socket.sendall(buffer)

    except ConnectionRefusedError:
        print(f"{sender} Couldn't connect to " f"{host}:{port}.")


if __name__ == "__main__":
    start_port = 3000
    # +1 for the leader/manager
    ports = [start_port + i for i in range(NUM_ELVES + 1)]

    threads = []

    for i, port in enumerate(ports):
        # Create a list of otherNodeAddrs for each ElfWorker
        nodeAddr = f"{LOCAL_HOST}:{port}"
        otherNodeAddrs = [f"{LOCAL_HOST}:{p}" for p in ports if p != port]
        # print(f"ELF: {nodeAddr} - otherNodeAddrs: {otherNodeAddrs}")

        # Create a new ReplList and ReplLockManager data structures
        elf_worker = ElfWorker(nodeAddr, otherNodeAddrs, consumers=[
                               ReplLockManager(autoUnlockTime=75.0)])

        # Create a new thread for each ElfWorker and add it to the list
        thread = threading.Thread(target=elf_worker.run, daemon=True)
        threads.append(thread)

    # Start all the threads
    for thread in threads:
        thread.start()

    # Join all the threads
    for thread in threads:
        thread.join()