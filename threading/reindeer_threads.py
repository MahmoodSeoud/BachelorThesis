import socket
import socketserver
import struct
import sys
import threading
import time
import random
import logging
from functools import partial
from pysyncobj import SyncObj, SyncObjConf, FAIL_REASON, replicated
from pysyncobj.batteries import ReplLockManager, ReplSet

NUM_REINDEER = 3  # 9
LOCAL_HOST = "127.0.0.1"
SANTA_PORT = 29800
LOGFILE = sys.argv[1]

logger = logging.getLogger(__name__)
logging.basicConfig(
    format="%(levelname)s %(asctime)s %(message)s",
    datefmt="%d/%m/%Y %H:%M:%S",
    filename=LOGFILE,
    filemode="w",
    encoding="utf-8",
    level=logging.DEBUG,
)


class ThreadedReindeerTCPRequestHandler(socketserver.StreamRequestHandler):

    def handle(self):
       # self.request.settimeout(10)  # Set the timout for the connection
        data = self.request.recv(1024)
        message = data.decode("utf-8")
        syncObj = self.server.syncObj
        client_ip, client_port = self.client_address

        logger.info(f"Received a message: {message}")
        print(f"Received a message: {message}")

        if message == "SYN": # Request to add new node
            buffer = bytearray()
            buffer.extend("ACK".encode())
            nodesInCluster = syncObj.otherNodes + [syncObj.selfNode]
            print("nodesInCluster",nodesInCluster)
            for node in nodesInCluster:
                buffer.extend(struct.pack("!I", node))

            #for node in nodesInCluster:
            #    node_str = f"{node.host}:{node.port}"
            #    buffer.extend(node_str.encode())
            
            send_message(client_ip, client_port, buffer)

        elif message == "SYN/ACK":
            new_node = f"{client_ip}:{client_port}"
            print(f"New node: {new_node}")
            syncObj.AddNodeToCluster(
                new_node, 
                callback=partial(onNodeAdded, node=reindeer_worker.selfNode)
            )
            
            NUM_REINDEER += 1

class ThreadedReindeerTCPNewNodeHandler(socketserver.StreamRequestHandler):

    def handle(self):
        data = self.request.recv(1024)
        message = data.decode("utf-8")
        client_ip, client_port = self.client_address
        ack, nodes = message.split("|")

        print(f"Received a message: {ack}")
        print(f"Nodes: {nodes}")

        if ack == "ACK":
            buffer = bytearray()
            buffer.extend("SYN/ACK".encode())
            send_message(client_ip, client_port, buffer)
            # Done making the connections
            self.server.server_close()

class ThreadedReindeeerTCPWorker(SyncObj):
    def __init__(self, node, otherNodes, consumers, extra_port, isNewNode=False):
        super(ThreadedReindeeerTCPWorker, self).__init__(
            node,
            otherNodes,
            consumers=consumers,
            conf=SyncObjConf(
                dynamicMembershipChange=True,
                connectionRetryTime=10.0,
            ),
        )

        self._is_awake = False
        self._extra_port = extra_port
        self._isNewNode = isNewNode

    def contact_santa(self, ports):
        reindeer_ports_as_list = list(ports)
        # reindeer_ports_as_list.append(self._extra_port)

        buffer = bytearray()
        buffer.extend("R".encode())

        # Append how many to contact
        buffer.extend(struct.pack("!I", len(reindeer_ports_as_list)))
        # Append the ports to contact
        for port in reindeer_ports_as_list:
            buffer.extend(struct.pack("!I", port))

        send_message(LOCAL_HOST, SANTA_PORT, buffer)


def onNodeAdded(result, error, node):
    if error == FAIL_REASON.SUCCESS:
        logger.info(f"ADDED - REQUEST [SUCCESS]: {node}, result: {result}")
    else:
        logger.error(
            f"ADDED - REQUEST [FAILED]: {node}, error: {error}, result: {result}"
        )


def send_message(targetHost, targetPort, buffer):
    try:
        print(f"Sending message to {targetHost}:{targetPort}")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as conn_socket:
            conn_socket.connect((targetHost, targetPort))
            conn_socket.sendall(buffer)

    except ConnectionRefusedError:
        logger.exception(f"Couldn't connect to: {targetHost}:{port}.")


def main(reindeer_worker):
    print(f"Running reindeer worker {reindeer_worker.selfNode}")
    print(f"Extra port: {reindeer_worker._extra_port}")

    while True:
        if not reindeer_worker.isReady():
            continue

        # Check if there's a leader, if not, continue waiting
        leader = reindeer_worker._getLeader()
        if leader is None:
            continue

        ## Removed the randomsleep for testing purposes
        sleep_time = random.randint(1, 5)
        # time.sleep(sleep_time)

        if len(woke.rawData()) < NUM_REINDEER and not reindeer_worker._is_awake:
            woke.add(
                (reindeer_worker._extra_port, sleep_time),
                callback=partial(onNodeAdded, node=reindeer_worker.selfNode),
            )
            reindeer_worker._is_awake = True

        if reindeer_worker._is_awake and len(woke.rawData()) == NUM_REINDEER:
            last_reindeer = max(woke.rawData(), key=lambda x: x[1])

            if last_reindeer[0] == reindeer_worker._extra_port:
                # Contat Santa
                ports = [item[0] for item in woke.rawData()]
                reindeer_worker.contact_santa(ports)
                reindeer_worker._is_awake = False
                woke.clear()

            reindeer_worker._is_awake = False


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(
            "Usage: %s logFilePath [--new] self_port partner1_port partner2_port ..."
            % sys.argv[0]
        )
        sys.exit(-1)

    # Introduction of new nodes
    if sys.argv[2] == "--new":
        node = int(sys.argv[3]) # New node
        otherNodes = sys.argv[4:] # List of other nodes
        randomOtherNode = int(otherNodes[random.randint(0, len(otherNodes)-1)])

        server = socketserver.ThreadingTCPServer(
            (LOCAL_HOST, node + 1), ThreadedReindeerTCPNewNodeHandler
        )

        buffer = bytearray()
        buffer.extend("SYN".encode())
        send_message(LOCAL_HOST, randomOtherNode + 1, buffer)

        with server:
            try:
                logger.info(
                    f"Starting listener: ({LOCAL_HOST}:{node +1})"
                )
                server.serve_forever()
            finally:
                server.server_close()

    
    node = f"{LOCAL_HOST}:{sys.argv[2]}"
    otherNodes = [f"{LOCAL_HOST}:{p}" for p in sys.argv[3:]]

    port = int(sys.argv[2])
    lock_manager = ReplLockManager(autoUnlockTime=10.0)
    woke = ReplSet()
    reindeer_worker = ThreadedReindeeerTCPWorker(
        node, otherNodes, consumers=[lock_manager, woke], extra_port=port + 1
    )

    thread = threading.Thread(target=main, args=(reindeer_worker,))
    thread.start()

    # handler = partial(ThreadedReindeerTCPRequestHandler, reindeer_worker)
    server = socketserver.ThreadingTCPServer(
        (LOCAL_HOST, reindeer_worker._extra_port), ThreadedReindeerTCPRequestHandler
    )
    server.syncObj = reindeer_worker

    with server:
        try:
            logger.info(
                f"Starting listener: ({LOCAL_HOST}:{reindeer_worker._extra_port})"
            )
            server.serve_forever()
        finally:
            server.server_close()

    thread.join()
