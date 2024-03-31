from __future__ import print_function
from pysyncobj.batteries import ReplPriorityQueue, ReplLockManager, ReplSet
from pysyncobj import SyncObj, SyncObjException, SyncObjConf, FAIL_REASON, replicated

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

class ReusableThreadingTCPServer(socketserver.ThreadingTCPServer):
    def __init__(self, server_address, RequestHandlerClass, bind_and_activate=True):
        # Call base constructor
        socketserver.ThreadingTCPServer.__init__(self, server_address, RequestHandlerClass, bind_and_activate=False)

        # Set SO_REUSEADDR option
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        if bind_and_activate:
            try:
                self.server_bind()
                self.server_activate()
            except:
                self.server_close()
                raise



class ElfContacter(SyncObj):

    def __init__(self, nodeAddr, otherNodeAddrs, consumers, message_queue):
        cfg = SyncObjConf(dynamicMembershipChange=True, connectionRetryTime=10, )

        super(ElfContacter, self).__init__(nodeAddr, otherNodeAddrs, consumers=[message_queue],conf=cfg)
        self._partners = otherNodeAddrs
        self.consumers = consumers
        self.ready_to_regroup = False
        self.first_time = True
        self.message_queue = message_queue

    # Class for handling the connection between the elves and Santa
    class RequestHandler(socketserver.StreamRequestHandler):
        def handle(self):
            identifier = self.request.recv(1).decode() # Recieving the identifier
            if identifier == 'S': # S for Santa
                data = self.request.recv(1024)

            elif identifier == 'L': # L for Leader
                data = self.request.recv(1024)
            
            print(f"[CHAIN CLUSTER] Recieved a message from Santa: {data.decode('utf-8')}")

    @replicated
    def set_ready_to_regroup(self, value):
        self.ready_to_regroup = value

    def get_ready_to_regroup(self):
        return self.ready_to_regroup

    # Function for the elf to listen for Santa
    def listener(self):
        print("I am tring something", self.selfNode)

        # Start server side
        with socketserver.ThreadingTCPServer((LOCAL_HOST, CHAIN_LEADER_PORT), self.RequestHandler
                                             ) as server:
            print(
                f"[CHAIN CLUSTER] - {self.selfNode} - Starting listener: ({LOCAL_HOST}:{CHAIN_LEADER_PORT})")
            try:
                server.handle_request()  # Server will handle the request from Santa and then closke
            finally:
                server.server_close()
                print(f"Closed server - {self.selfNode}")

    # Function for the elf to contact Santa
    def contact_santa(self):
        # Sent msg to Santa whom then msg's back here so that we can notify_all()
        try:
            print(
                f"[CHAIN CLUSTER] - {self.selfNode} - Connecting to Santa at: "
                f"{LOCAL_HOST}:{SANTA_PORT}"
            )
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as conn_socket:

                conn_socket.connect((LOCAL_HOST, SANTA_PORT))

                identifier = "E"  # E for elves as identifier
                buffer = bytearray()
                buffer.extend(identifier.encode())

                conn_socket.sendall(buffer)

        except ConnectionRefusedError:
            print(
                f"[CHAIN CLUSTER]-  Couldn't connect at: "
                f"{LOCAL_HOST}:{SANTA_PORT}"
            )

    # Function for the elf to listen for Santa
    def listen_leader(self):
        # Start server side
        with socketserver.ThreadingTCPServer((LOCAL_HOST, CHAIN_LEADER_PORT), self.RequestHandler
                                             ) as server:

            print(
                f"[CHAIN CLUSTER] - {self.selfNode} - Starting listener: ({LOCAL_HOST}:{CHAIN_LEADER_PORT})")
            server.message_queue = self.message_queue
            try:
                server.handle_request()  # Server will handle the request from Santa and then closke
            finally:
                server.server_close()
                print(f"Closed LeaderServer - {self.selfNode}")
    

    def contact_leader(self):
        # Sent msg to leader elf whom is going to add us back to the cluster
        try:
            print(
                f"ELF: {self.selfNode} -  Connecting to main cluster leader at: "
                f"{LOCAL_HOST}:{MAIN_LEADER_PORT}"
            )
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as conn_socket:

                conn_socket.connect((LOCAL_HOST, MAIN_LEADER_PORT))

                # node_bytes = pickle.dumps(self.selfNode)  # Serialize TCPNode to bytes
                
                buffer = bytearray()
                buffer.append(0)
                # buffer.extend(node_bytes)

                conn_socket.sendall(buffer)

        except ConnectionRefusedError:
            print(
                f"[CHAIN CLUSTER] -  Couldn't connect at: "
                f"{LOCAL_HOST}:{MAIN_LEADER_PORT}"
            )

    def start_threads(self):
        sub_threads1 = [
            threading.Thread(target=self.listener),
            threading.Thread(target=self.contact_santa),
        ]

        sub_threads2 = [
            threading.Thread(target=self.listener),
            threading.Thread(target=self.contact_leader),
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
        print(f"ELF: {self.selfNode} - otherNodeAddrs: {self._partners}")
        print(f"ELF: {self.selfNode} - Running ElfContacter")

        while True:
            time.sleep(0.5)

            if self.get_ready_to_regroup():
                for partner in self._partners:
                    self.removeNodeFromCluster(
                        partner, callback=partial(onNodeRemoved, node=partner))
                # TODO: This should not be self._partners but rather what the main clust leader has in its list
                ElfWorker(self.selfNode, self._partners, self.consumers).run() 
                self.destroy()
                break

            if self._getLeader() is None:
                continue

            if self._isLeader() and self.first_time:
                # TODO: Maybe add a lock around this
                self.first_time = False
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
                connectionTimeout=12,
            ),
        )
        self.node_chain = consumers[0]
        self.queue = consumers[1]
        self.lockManager = consumers[2]
        self.consumers = consumers
        self._memberOfCluster = True
        self._hasAppended = False
        self.first_time = True
        self._mainCluster = otherNodeAddrs

     # Class for handling the connection between the elves and Santa

    class RequestHandler(socketserver.StreamRequestHandler):
        def handle(self):
            print("[MAIN CLUSTER] Recieved a message from a chain cluster")

    def main_cluster_listener(self):
        # Start server side
        with socketserver.ThreadingTCPServer(
            (LOCAL_HOST, MAIN_LEADER_PORT), self.RequestHandler
        ) as server:
            print(
                f"[MAIN CLUSTER] -  Starting elf listener: {LOCAL_HOST}:{MAIN_LEADER_PORT}")
            try:
                server.handle_request()  # Server will handle the request from Santa and then closke
            finally:
                server.server_close()

                for node in self.node_chain.rawData():
                    self.node_chain.pop()

                for node in self.node_chain.rawData():
                    self.addNodeToCluster(node, callback=partial(onNodeAdded, node=node))

    def contact_chain_cluster_leader(self):
      # Sent msg to leader elf whom is going to add us back to the cluster
        try:
            print(
                f"ELF: {self.selfNode} -  Connecting to chain cluster leader at: "
                f"{LOCAL_HOST}:{CHAIN_LEADER_PORT}"
            )
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as conn_socket:

                conn_socket.connect((LOCAL_HOST, CHAIN_LEADER_PORT))

                # node_bytes = pickle.dumps(self.selfNode)  # Serialize TCPNode to bytes
                _identifier = "L"  # L for leader as identifier

                allNodes = [self.selfNode] + self.otherNodes
                node_bytes = pickle.dumps(allNodes)

                buffer = bytearray()
                buffer.extend(_identifier.encode())
                buffer.extend(node_bytes)

                conn_socket.sendall(buffer)

        except ConnectionRefusedError:
            print(
                f"[CHAIN CLUSTER] -  Couldn't connect at: "
                f"{LOCAL_HOST}:{CHAIN_LEADER_PORT}"
            )

    def run(self):
        while True:
            time.sleep(0.5)

            if self._getLeader() is None:
                # Nodes without a leader should wait until one is elected
                # Could also be the case that this node is consulting Santa
                continue
            
            if self._isLeader() and self.first_time:
                self.first_time = False
                sub_threads = [
                threading.Thread(target=self.main_cluster_listener),
                #threading.Thread(target=self.contact_chain_cluster_leader),
                ]

                for sub_thread in sub_threads:
                    sub_thread.start()

                for sub_thread in sub_threads:
                    sub_thread.join()
                #threading.Thread(target=self.main_cluster_listener).start()

            # print(f"Elf{self.selfNode} has a list: {self.node_chain.rawData()}")
            # print(f"leader is: {self._getLeader()}")

            # If the list is full and the node is not in the list, remove nodes from the list
            if len(self.node_chain.rawData()) == 3:
                chain_members = [p for p in self.node_chain.rawData()]
                # Remove nodes from the list
                for node in chain_members:
                    self.removeNodeFromCluster(
                        node, callback=partial(onNodeRemoved, node=node)
                    )

            if (
                len(self.node_chain.rawData()
                    ) == 3 and self.selfNode in self.node_chain.rawData()
            ):
                print(f"ELF: {self.selfNode} - I am in the list")

                self.destroy()
                node_partners = [
                    p for p in self.node_chain.rawData() if p != self.selfNode]
                ElfContacter(self.selfNode, node_partners, self.consumers, ReplPriorityQueue()).run()
                print(f"ELF: {self.selfNode} - IS BACK AT AGAIN")

            if not self._isLeader():
                try:
                    if self.lockManager.tryAcquire("testLockName", sync=True):
                        if len(self.node_chain.rawData()) < 3:
                            self.node_chain.add(self.selfNode, callback=partial(
                                onAdd, node=self.selfNode))
                        elif len (self.node_chain.rawData()) == 3:
                            self.queue.put(self.node_chain.rawData(), _doApply=True)
                            self.node_chain.clear()
                except:
                    print(f"ELF: {self.selfNode} - Failed to acquire lock")
                finally:
                    if self.lockManager.isAcquired("testLockName"):
                        self.lockManager.release("testLockName")


def onAdd(result, error, node):
    if error == FAIL_REASON.SUCCESS:
        print(f"Append - REQUEST [SUCCESS]: {node}")


def onNodeAdded(result, error, node):
    if error == FAIL_REASON.SUCCESS:
        print(f"Added - REQUEST [SUCCESS]: {node}")


def onNodeRemoved(result, error, node):
    if error == FAIL_REASON.SUCCESS:
        print(f"Removal - REQUEST [SUCCESS]: {node}")


if __name__ == "__main__":
    start_port = 3000
    ports = [start_port + i for i in range(NUM_ELVES)]

    threads = []

    for i, port in enumerate(ports):
        # Create a list of otherNodeAddrs for each ElfWorker
        nodeAddr = f"{LOCAL_HOST}:{port}"
        otherNodeAddrs = [f"{LOCAL_HOST}:{p}" for p in ports if p != port]
        print(f"ELF: {nodeAddr} - otherNodeAddrs: {otherNodeAddrs}")

        # Create a new ReplList and ReplLockManager data structures
        set = ReplSet()
        queue = ReplPriorityQueue()
        lockManager = ReplLockManager(autoUnlockTime=75)

        # Create a new ElfWorker
        elf_worker = ElfWorker(nodeAddr, otherNodeAddrs, [set, queue, lockManager])

        # Create a new thread for each ElfWorker and add it to the list
        thread = threading.Thread(target=elf_worker.run, daemon=True)
        threads.append(thread)

    # Start all the threads
    for thread in threads:
        thread.start()

    # Join all the threads
    for thread in threads:
        thread.join()
