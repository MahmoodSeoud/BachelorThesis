from __future__ import print_function
from queue import Queue
from pysyncobj import SyncObj, SyncObjException, SyncObjConf, FAIL_REASON, replicated
from pysyncobj.batteries import ReplLockManager

import sys
import threading
import struct
import socketserver
import socket
import pickle
import time
import random
from functools import partial

sys.path.append("../")
LOCAL_HOST = "127.0.0.1"

MAIN_LEADER_PORT = 8000
CHAIN_LEADER_PORT = 8888
SANTA_PORT = 29800

NUM_ELVES = 7

allNodes = []


class ElfContacter(SyncObj):

    def __init__(self, nodeAddr, otherNodeAddrs, consumers):
        cfg = SyncObjConf(dynamicMembershipChange=True,
                          connectionRetryTime=5)

        super(ElfContacter, self).__init__(
            nodeAddr, otherNodeAddrs, conf=cfg)
        self.partners = otherNodeAddrs
        self.consumers = consumers
        self.ready_to_regroup = False
        self.first_time = True

    # Class for handling the connection between the elves and Santa
    class RequestHandler(socketserver.StreamRequestHandler):
        def handle(self):
            identifier = self.request.recv(
                1).decode()  # Recieving the identifier

            data = self.request.recv(1024)

            if identifier == 'S':  # S for Santa
                message = data.decode('utf-8')
                print(
                    f"[CHAIN CLUSTER] Received a message from Santa: {message}")

            elif identifier == 'L':  # L for Leader
                mainClusterNodes = pickle.loads(data)
                print(f"[CHAIN CLUSTER] Received a message from Leader: {
                      mainClusterNodes}")
                allNodes.clear()
                allNodes.extend(mainClusterNodes)

    @replicated
    def set_ready_to_regroup(self, value):
        self.ready_to_regroup = value

    def remove_nodes(self, nodes_to_remove):
        for partner in nodes_to_remove:
            self.removeNodeFromCluster(
                partner, callback=partial(onNodeRemoved, node=partner, cluster="chain"))

    def get_ready_to_regroup(self):
        return self.ready_to_regroup

    # Function for the elf to listen for Santa
    def listener(self, host, port):
        with socketserver.ThreadingTCPServer((host, port), self.RequestHandler) as server:
            print(
                f"[CHAIN CLUSTER] - {self.selfNode} - Starting listener: ({host}:{port})")
            try:
                server.handle_request()  # Server will handle the request from Santa and then close
            finally:
                server.server_close()
                print(f"Closed LeaderServer - {self.selfNode}")

    def contact_entity(self, host, port, identifier):
        # print(f"[CHAIN CLUSTER] - {self.selfNode} - Connecting to entity at: {host}:{port}")
        buffer = bytearray()
        buffer.extend(identifier.encode())
        send_message(self.selfNode, host, port, buffer)

    def start_threads(self):
        sub_threads1 = [
            threading.Thread(target=self.listener, args=(
                LOCAL_HOST, CHAIN_LEADER_PORT)),
            threading.Thread(target=self.contact_entity,
                             args=(LOCAL_HOST, SANTA_PORT, 'E')),
        ]

        sub_threads2 = [
            threading.Thread(target=self.listener, args=(
                LOCAL_HOST, CHAIN_LEADER_PORT)),
            threading.Thread(target=self.contact_entity, args=(
                LOCAL_HOST, MAIN_LEADER_PORT, 'E')),
        ]

        for sub_thread in sub_threads1:
            sub_thread.start()

        for sub_thread in sub_threads1:
            sub_thread.join()

        for sub_thread in sub_threads2:
            sub_thread.start()

        for sub_thread in sub_threads2:
            sub_thread.join()

    def run(self):
        # print(f"ELF: {self.selfNode} - otherNodeAddrs: {self.partners}")
        print(f"ELF: {self.selfNode} - Running ElfContacter")

        while True:
            time.sleep(0.5)

            if self._getLeader() is None:
                continue

            if self.get_ready_to_regroup():

                self.remove_nodes(self.partners)

                allNodes.extend(self.partners)
                allNodes.append(self.selfNode)
                # ElfWorker(self.selfNode, allNodes, self.consumers).run()
                self.destroy()
                break

            if self._isLeader() and not self.get_ready_to_regroup():
                # TODO: Maybe add a lock around this
                self.start_threads()
                self.set_ready_to_regroup(True)


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

    def dequeue(self):
        return self.__queue.get()

    @replicated
    def set_chain_is_out(self, value):
        self.chain_is_out = value

    def getQueueSize(self):
        return self.__queue.qsize()

    def getChain(self):
        return self.__chain

    def get_chain_is_out(self):
        return self.chain_is_out


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

    def main_cluster_listener(self):
        # Start server side
        # self.server = socketserver.TCPServer((LOCAL_HOST, MAIN_LEADER_PORT), lambda *args, **kwargs: self.RequestHandler(*args, server=self, **kwargs))
        with socketserver.ThreadingTCPServer(
            (LOCAL_HOST, MAIN_LEADER_PORT), self.RequestHandler
        ) as server:
            print(
                f"[MAIN CLUSTER] - {self.selfNode} - Starting elf listener: {LOCAL_HOST}:{MAIN_LEADER_PORT}")
            try:
                # TODO: Maybe change this to server_forever()
                server.handle_request()  # Server will handle the request from Santa and then closke
            finally:
                server.server_close()

    def contact_chain_cluster_leader(self):

        identifier = 'L'  # L for leader as identifier
        mainClusterNodes = [self.selfNode] + list(self.otherNodes)
        node_bytes = pickle.dumps(mainClusterNodes)
        buffer = bytearray()
        buffer.extend(identifier.encode())
        buffer.extend(node_bytes)
        send_message(self.selfNode, LOCAL_HOST, CHAIN_LEADER_PORT, buffer)

 
    def run(self):
        while self.isAlive:
            time.sleep(0.5)

            if self._getLeader() is None:
                # Nodes without a leader should wait until one is elected
                continue
            
            print(f"ELF: {self.selfNode} - queue size: {self.getQueueSize()} - count: {self.getStatus()['partner_nodes_count']}")
            if self.getQueueSize() > 0 and self.get_chain_is_out() is False:
                self.set_chain_is_out(True)
                chain = self.dequeue()
                print(f"ELF: {self.selfNode} - Dequeueing - {chain}")
                
                print('chain', chain)
                # Remove nodes from the list
                for node in chain:
                    self.removeNodeFromCluster(
                        node, callback=partial(onNodeRemoved, node=node, cluster="main"))
                #if self.selfNode in chain:
                #    print(f"ELF: {self.selfNode} - Im in the list")
                #    self.destroy()
                # TODO: Create a new ElfContacter
                self.clearChain()


            try:
                if self.lock_manager.tryAcquire("chainLock", sync=True):
                    if not self._isLeader():
                        if len(self.getChain()) < 3:
                            self.addNodeToChain(self.selfNode, callback=partial(
                                onNodeAdded, node=self.selfNode, cluster="chain"))
                            # 3 is the number of nodes in a chain
                            # If the chain is full, add it to the queue
                            # (+1) since it has not been added yet
                        elif len(self.getChain()) == 3: 
                                self.enqueue(self.getChain())
            except Exception as e:
                print(f"ELF: {self.selfNode} - Could not acquire lock: {e}")
            finally:
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


def send_message(selfNode, host, port, buffer):
    try:
        print(f'{selfNode} - connecting to {host}:{port}')
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as conn_socket:
            conn_socket.connect((host, port))
            conn_socket.sendall(buffer)

    except ConnectionRefusedError:
        print(f"{selfNode} - Couldn't connect to " f"{host}:{port}.")


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
