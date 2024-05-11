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
            logger.info(f"Received a message from Santa: {message}")

    def listener(self, host, port):
        with socketserver.ThreadingTCPServer(
            (host, port), self.RequestHandler
        ) as server:
            logger.info(f"[{self.sender}] - Starting listener: ({host}:{port})")
            try:
                server.handle_request()  # Server will handle the request from Santa and then close
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

    def run(self):
        self.start_threads()


class ReindeerWorker(SyncObj):
    def __init__(self, node, otherNodes, consumers, extra_port):
        super(ReindeerWorker, self).__init__(
            node,
            otherNodes,
            consumers=consumers,
            conf=SyncObjConf(
                connectionRetryTime=10.0,
            ),
        )

        self._extra_port = extra_port
        self._all_reindeer_awake = False
        self._last_reindeer_awake = None

    @replicated
    def setAllReindeerAwake(self, state):
        self._all_reindeer_awake = state
        return self._all_reindeer_awake

    @replicated
    def setLastReindeerAwake(self, state):
        self._last_reindeer_awake = state
        return self._last_reindeer_awake

    def getLastReindeerAwake(self):
        return self._last_reindeer_awake

    def getAllReindeerAwake(self):
        return self._all_reindeer_awake


def send_message(sender, targetHost, targetPort, buffer):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as conn_socket:
            conn_socket.connect((targetHost, targetPort))
            conn_socket.sendall(buffer)

    except ConnectionRefusedError:
        logger.exception(f"{sender} Couldn't connect to: {targetHost}:{port}.")


def onNodeAdded(result, error, node):
    if error == FAIL_REASON.SUCCESS:
        logger.info(f"ADDED - REQUEST [SUCCESS]: {node}, result: {result}")
    else:
        logger.error(
            f"ADDED - REQUEST [FAILED]: {node}, error: {error}, result: {result}"
        )


def runReindeerContacter(port, reindeer_ports):
    ReinderContacter(port, reindeer_ports).run()


def runReindeerListener(port):
    ReinderContacter(port).listener(LOCAL_HOST, port)


def run(reindeer_worker):
    print(f"Running reindeer worker {reindeer_worker.selfNode}")
    print(f"Extra port: {reindeer_worker._extra_port}")

    while True:
        time.sleep(0.5)
        sleep_time = random.randint(1, 5)

        leader = reindeer_worker._getLeader()
        if leader is None:
            continue

        try:
            if lock_manager.tryAcquire("reindeerLock", sync=True):

                if len(woke.rawData()) < NUM_REINDEER:
                    woke.add(
                        (reindeer_worker._extra_port, sleep_time),
                        callback=partial(onNodeAdded, node=reindeer_worker.selfNode),
                    )

                    if len(woke.rawData()) + 1 == NUM_REINDEER:
                        # Find the reindeer with the longest sleep time.
                        last_awake_reindeer = max(
                            woke.rawData(), key=lambda item: item[1]
                        )
                        reindeer_worker.setLastReindeerAwake(last_awake_reindeer)
                        reindeer_worker.setAllReindeerAwake(True)

                # Release the lock
                lock_manager.release("reindeerLock")

                while not reindeer_worker.getAllReindeerAwake():
                    time.sleep(0.5)

                if (
                    reindeer_worker.getLastReindeerAwake()[0]
                    == reindeer_worker._extra_port
                ):
                    # Contat Santa
                    ports = [item[0] for item in woke.rawData()]
                    runReindeerContacter(reindeer_worker._extra_port, ports)

                    # Reset the woke set and set all reindeer to sleep
                    woke.clear()
                    reindeer_worker.setAllReindeerAwake(False)
                    reindeer_worker.setLastReindeerAwake(None)
                else:
                    # Listen to santa
                    runReindeerListener(reindeer_worker._extra_port)

        except Exception as e:
            logger.error(f"Could not acquire lock due to error: {e}")
        finally:
            if lock_manager.isAcquired("reindeerLock"):
                lock_manager.release("reindeerLock")


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
