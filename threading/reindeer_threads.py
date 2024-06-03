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

        logger.info(f"Received a message: {message}")
        print(f"Received a message: {message}")

        if message[:2] == "SYN":  # Request to add new node
            _ , data_port = message.split(':')
            print('dataPort:', data_port)
            buffer = bytearray()

            new_node = f"{LOCAL_HOST}:{data_port}"
            syncObj.AddNodeToCluster(
                new_node, callback=partial(onNodeAdded, node=reindeer_worker.selfNode)
            )
            NUM_REINDEER += 1

            nodesInCluster = + [syncObj.selfNode] + list(syncObj.otherNodes) 
            for node in nodesInCluster:
                buffer.extend(struct.pack("!I", node.port))

            send_message(LOCAL_HOST, data_port, buffer)

        elif message[:6] == "SYN/ACK":
            print("Received SYN/ACK")


class ThreadedReindeerTCPNewNodeHandler(socketserver.StreamRequestHandler):

    def handle(self):
        data = self.request.recv(1024)
        message = data.decode("utf-8")
        print(f"Received a message: {message}")

        buffer = bytearray()
        buffer.extend("SYN/ACK".encode())
        #Ksend_message(LOCAL_HOST, data_port, buffer)
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


def contact_reindeer(myPort, targetPort):
    buffer = bytearray()
    buffer.extend("SYN".encode())
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
        #print(f"Other nodes: {reindeer_worker.otherNodes}")
        print('partner_nodes_count', reindeer_worker.getStatus()['partner_nodes_count'])

        ## Removed the randomsleep for testing purposes
        #sleep_time = random.randint(1, 5)
        ## time.sleep(sleep_time)

        #if len(woke.rawData()) < NUM_REINDEER and not reindeer_worker._is_awake:
        #    woke.add(
        #        (reindeer_worker._extra_port, sleep_time),
        #        callback=partial(onNodeAdded, node=reindeer_worker.selfNode),
        #    )
        #    reindeer_worker._is_awake = True

        #if reindeer_worker._is_awake and len(woke.rawData()) == NUM_REINDEER:
        #    last_reindeer = max(woke.rawData(), key=lambda x: x[1])

        #    if last_reindeer[0] == reindeer_worker._extra_port:
        #        # Contat Santa
        #        ports = [item[0] for item in woke.rawData()]
        #        reindeer_worker.contact_santa(ports)
        #        reindeer_worker._is_awake = False
        #        woke.clear()

        #    reindeer_worker._is_awake = False


def listener(server,host, port):

    with server:
        try:
            logger.info(
                f"Starting listener: ({host}:{port})"
            )
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
        node = int(sys.argv[3])  # New node
        otherNodes = sys.argv[4:]  # List of other nodes
        randomOtherNode = int(otherNodes[random.randint(0, len(otherNodes) - 1)])

        newNodeServer = socketserver.ThreadingTCPServer(
            (LOCAL_HOST, node + 1), ThreadedReindeerTCPNewNodeHandler
        )

        threads = [
            threading.Thread(target=listener, args=(newNodeServer, LOCAL_HOST, node + 1)),
            threading.Thread(target=contact_reindeer, args=(node, randomOtherNode)),
        ]        

        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

    else:
        node = f"{LOCAL_HOST}:{sys.argv[2]}"
        otherNodes = [f"{LOCAL_HOST}:{p}" for p in sys.argv[3:]]

        port = int(sys.argv[2])
        lock_manager = ReplLockManager(autoUnlockTime=10.0)
        woke = ReplSet()
        reindeer_worker = ThreadedReindeeerTCPWorker(
            node, otherNodes, consumers=[lock_manager, woke], extra_port=port + 1
        )
        # Kjkprint('RUNNING')
        # DONT WANT TO BURN MY COMPUTER DOWN WHILE TESTING

        reindeerServer = socketserver.ThreadingTCPServer(
            (LOCAL_HOST, reindeer_worker._extra_port), ThreadedReindeerTCPRequestHandler
        )
        reindeerServer.syncObj = reindeer_worker

        threads = [
            threading.Thread(target=main, args=(reindeer_worker,)),
            threading.Thread(target=listener, args=(reindeerServer, LOCAL_HOST, reindeer_worker._extra_port)),
        ]

        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()


