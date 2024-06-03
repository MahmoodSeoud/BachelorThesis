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

NUM_REINDEER = 9
LOCAL_HOST = "127.0.0.1"
SANTA_PORT = 29800
LOGFILE = sys.argv[1]


NODES_TO_JOIN = []

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
        identifier = self.request.recv(1).decode()  # Recieving the identifier
        print("identifier:", identifier)

        if identifier == "S":  # Request to add new node
            self.handleSYN()
        elif identifier == "/":
            self.handleSYNACK()

        elif identifier == "C":  # From Santa
            data = self.request.recv(1024)
            message = data.decode("utf-8")
            logger.info(f"Received a message: {message}")
            print(f"Received a message: {message}")

    def handleSYN(self):
        payload = self.request.recv(1024)
        syncObj = self.server.syncObj
        data_port = struct.unpack("!I", payload[:4])[0]

        print("dataPort:", data_port)
        buffer = bytearray()

        new_node = f"{LOCAL_HOST}:{data_port}"
        syncObj.addNodeToCluster(
            new_node,
            callback=partial(onNodeAdded, node=reindeer_worker_server.selfNode),
        )

        global NUM_REINDEER
        NUM_REINDEER += 1

        nodesInCluster = [syncObj.selfNode] + list(syncObj.otherNodes)
        buffer.extend(struct.pack("!I", len(nodesInCluster)))
        for node in nodesInCluster:
            buffer.extend(struct.pack("!I", node.port))

        send_message(LOCAL_HOST, data_port + 1, buffer)

    def handleSYNACK(self):
        print("Received SYN/ACK")


class ThreadedReindeerTCPNewNodeHandler(socketserver.StreamRequestHandler):

    def handle(self):
        payload = self.request.recv(1024)
        # message = payload.decode("utf-8")

        amount_of_peers = struct.unpack("!I", payload[:4])[
            0
        ]  # amount of nodes to contact
        peer_ports = struct.unpack(
            f"!{amount_of_peers}I", payload[4 : 4 + 4 * amount_of_peers]
        )

        print("peer_ports:", peer_ports)

        buffer = bytearray()
        buffer.extend("/".encode())  # Send the SYN/ACK
        send_message(LOCAL_HOST, peer_ports[0] + 1, buffer)

        # Done making the connections
        self.server.shutdown()
        global NODES_TO_JOIN
        NODES_TO_JOIN = peer_ports

    def handleACK(self):
        pass


class ThreadedReindeerTCPWorker(SyncObj):
    def __init__(self, node, otherNodes, consumers, extra_port):
        super(ThreadedReindeerTCPWorker, self).__init__(
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


def contact_reindeer(myPort, targetPort):
    buffer = bytearray()
    buffer.extend("S".encode())
    buffer.extend(struct.pack("!I", myPort))
    send_message(LOCAL_HOST, targetPort + 1, buffer)


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
        logger.exception(f"Couldn't connect to: {targetHost}:{targetPort}.")


def main(reindeer_worker_server):
    print(f"Running reindeer worker {reindeer_worker_server.selfNode}")
    print(f"Extra port: {reindeer_worker_server._extra_port}")
    while True:
        if not reindeer_worker_server.isReady():
            continue

        # Check if there's a leader, if not, continue waiting
        leader = reindeer_worker_server._getLeader()
        if leader is None:
            continue

        #print( "partner_nodes_count", reindeer_worker_server.getStatus()["partner_nodes_count"])

        ## Removed the randomsleep for testing purposes
        sleep_time = random.randint(1, 5)
        # time.sleep(sleep_time)

        if len(woke.rawData()) < NUM_REINDEER and not reindeer_worker_server._is_awake:
           woke.add(
               (reindeer_worker_server._extra_port, sleep_time),
               callback=partial(onNodeAdded, node=reindeer_worker_server.selfNode),
           )
           reindeer_worker_server._is_awake = True

        if reindeer_worker_server._is_awake and len(woke.rawData()) == NUM_REINDEER:
           last_reindeer = max(woke.rawData(), key=lambda x: x[1])

           if last_reindeer[0] == reindeer_worker_server._extra_port:
               # Contat Santa
               ports = [item[0] for item in woke.rawData()]
               reindeer_worker_server.contact_santa(ports)
               reindeer_worker_server._is_awake = False
               woke.clear()

           reindeer_worker_server._is_awake = False


def listener(server, host, port):

    with server:
        try:
            logger.info(f"Starting listener: ({host}:{port})")
            server.serve_forever()
        finally:
            server.server_close()


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(
            "Usage: %s logFilePath [--new] self_port partner1_port partner2_port ..."
            % sys.argv[0]
        )
        sys.exit(-1)

    # Introduction of new nodes
    if sys.argv[2] == "--new":
        my_port = int(sys.argv[3])  # New node
        otherNodes_ports = sys.argv[4:]  # List of other nodes
        randomOtherNode_port = int(otherNodes_ports[random.randint(0, len(otherNodes_ports) - 1)])

        newNodeServer = socketserver.ThreadingTCPServer(
            (LOCAL_HOST, my_port + 1), ThreadedReindeerTCPNewNodeHandler
        )

        threads = [
            threading.Thread(
                target=listener, args=(newNodeServer, LOCAL_HOST, my_port + 1)
            ),
            threading.Thread(target=contact_reindeer, args=(my_port, randomOtherNode_port)),
        ]

        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        node = f"{LOCAL_HOST}:{my_port}"
        otherNodes = [f"{LOCAL_HOST}:{p}" for p in NODES_TO_JOIN]

        lock_manager = ReplLockManager(autoUnlockTime=10.0)
        woke = ReplSet()

        reindeer_worker_server = ThreadedReindeerTCPWorker(
            node,
            otherNodes,
            consumers=[lock_manager, woke],
            extra_port=my_port + 1,
        )

        reindeer_listener_server = socketserver.ThreadingTCPServer(
            (LOCAL_HOST, reindeer_worker_server._extra_port),
            ThreadedReindeerTCPRequestHandler,
        )
        reindeer_listener_server.syncObj = reindeer_worker_server

        threads = [
            threading.Thread(target=main, args=(reindeer_worker_server,)),
            threading.Thread(
                target=listener,
                args=(
                    reindeer_listener_server,
                    LOCAL_HOST,
                    reindeer_worker_server._extra_port,
                ),
            ),
        ]

        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

    else:
        my_port = int(sys.argv[2])
        node = f"{LOCAL_HOST}:{my_port}"
        otherNodes = [f"{LOCAL_HOST}:{p}" for p in sys.argv[3:]]

        lock_manager = ReplLockManager(autoUnlockTime=10.0)
        woke = ReplSet()

        reindeer_worker_server = ThreadedReindeerTCPWorker(
            node, otherNodes, consumers=[lock_manager, woke], extra_port=my_port + 1
        )

        reindeer_listener_server = socketserver.ThreadingTCPServer(
            (LOCAL_HOST, reindeer_worker_server._extra_port),
            ThreadedReindeerTCPRequestHandler,
        )
        reindeer_listener_server.syncObj = reindeer_worker_server

        threads = [
            threading.Thread(target=main, args=(reindeer_worker_server,)),
            threading.Thread(
                target=listener,
                args=(
                    reindeer_listener_server,
                    LOCAL_HOST,
                    reindeer_worker_server._extra_port,
                ),
            ),
        ]

        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
