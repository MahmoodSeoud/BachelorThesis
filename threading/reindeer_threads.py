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

logger = logging.getLogger(__name__)
logging.basicConfig(
    format="%(levelname)s %(asctime)s %(message)s",
    datefmt="%d/%m/%Y %H:%M:%S",
    filename=LOGFILE,
    filemode="w",
    encoding="utf-8",
    level=logging.DEBUG,
)


class ReinderContacter:
    def __init__(self, sender, reindeer_ports=None):
        self.sender = sender
        self.reindeer_ports = reindeer_ports

    # Class for handling the connection between the elves and Santa
    class RequestHandler(socketserver.StreamRequestHandler):
        def handle(self):
            self.request.settimeout(10)  # Set the timout for the connection
            data = self.request.recv(1024)
            message = data.decode("utf-8")
            logger.info(f"Received a message: {message}")
            print(f"Received a message: {message}")

    def listener(self, host, port):
        logger.info(f"Starting listener: ({host}:{port})")
        with socketserver.ThreadingTCPServer(
            (host, port), self.RequestHandler
        ) as server:
            try:
                server.serve_forever()
            finally:
                server.server_close()

    def contact_santa(self, sender, targetHost, targetPort, reindeer_ports):
        reindeer_ports_as_list = list(reindeer_ports)
        reindeer_ports_as_list.append(sender)

        buffer = bytearray()
        buffer.extend("R".encode())
        for port in reindeer_ports_as_list:
            buffer.extend(struct.pack("!I", port))

        send_message(sender, targetHost, targetPort, buffer)

    def start_threads(self):
        sub_threads = [
            threading.Thread(target=self.listener, args=(LOCAL_HOST, self.sender)),
            threading.Thread(
                target=self.contact_santa,
                args=(self.sender, LOCAL_HOST, SANTA_PORT, self.reindeer_ports),
            ),
        ]

        for sub_thread in sub_threads:
            sub_thread.start()

        for sub_thread in sub_threads:
            sub_thread.join()


class ReindeerWorker(SyncObj):
    def __init__(self, node, otherNodes, consumers, extra_port):
        super(ReindeerWorker, self).__init__(
            node,
            otherNodes,
            consumers=consumers,
            conf=SyncObjConf(
                # dynamicMembershipChange=True,
                connectionRetryTime=10.0,
            ),
        )

        self._is_awake = False
        self._extra_port = extra_port


def runReindeerContacter(port, reindeer_ports):
    ReinderContacter(port, reindeer_ports).contact_santa(
        port, LOCAL_HOST, SANTA_PORT, reindeer_ports
    )


def runReindeerListener(port):
    ReinderContacter(port).listener(LOCAL_HOST, port)


def runReindeerMain(reindeer_worker):
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
                runReindeerContacter(reindeer_worker._extra_port, ports)
                reindeer_worker._is_awake = False
                woke.clear()

                # Listen to santa
                # runReindeerListener(reindeer_worker._extra_port)

            reindeer_worker._is_awake = False


def onNodeAdded(result, error, node):
    if error == FAIL_REASON.SUCCESS:
        logger.info(f"ADDED - REQUEST [SUCCESS]: {node}, result: {result}")
    else:
        logger.error(
            f"ADDED - REQUEST [FAILED]: {node}, error: {error}, result: {result}"
        )


def send_message(sender, targetHost, targetPort, buffer):
    try:
        print(f"Sending message to {targetHost}:{targetPort}")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as conn_socket:
            conn_socket.connect((targetHost, targetPort))
            conn_socket.sendall(buffer)

    except ConnectionRefusedError:
        logger.exception(f"{sender} Couldn't connect to: {targetHost}:{port}.")


def run(reindeer_worker):

    sub_threads = [
        threading.Thread(
            target=runReindeerListener,
            args=(reindeer_worker._extra_port,)
        ),
        threading.Thread(
            target=runReindeerMain,
            args=(reindeer_worker,),
        ),
    ]

    for sub_thread in sub_threads:
        sub_thread.start()

    for sub_thread in sub_threads:
        sub_thread.join()


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(
            "Usage: %s logFilePath self_port partner1_port partner2_port ..."
            % sys.argv[0]
        )
        sys.exit(-1)

    node = f"{LOCAL_HOST}:{sys.argv[2]}"
    otherNodes = [f"{LOCAL_HOST}:{p}" for p in sys.argv[3:]]

    port = int(sys.argv[2])
    lock_manager = ReplLockManager(autoUnlockTime=75.0)
    woke = ReplSet()
    reindeer_worker = ReindeerWorker(
        node, otherNodes, consumers=[lock_manager, woke], extra_port=port + 1
    )
    run(reindeer_worker)
