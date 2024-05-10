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
from pysyncobj.batteries import ReplLockManager, ReplList

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

isWoke = False

class ReinderContacter():
    def __init__(self, sender, reindeer_ports=None):
        self.sender = sender
        self.reindeer_ports = reindeer_ports

    # Class for handling the connection between the elves and Santa
    class RequestHandler(socketserver.StreamRequestHandler):
        def handle(self):
            self.request.settimeout(10)  # Set the timout for the connection
            data = self.request.recv(1024)
            message = data.decode("utf-8")
            logger.info(f"Reindeer Received a message from Santa: {message}")

    def listener(self, host, port):
        with socketserver.ThreadingTCPServer(
            (host, port), self.RequestHandler
        ) as server:
            logger.info(f"[{self.sender}] - Starting listener: ({host}:{port})")
            try:
                server.handle_request()  # Server will handle the request from Santa and then close
            finally:
                server.server_close()

    def contact_santa(self, sender, host, port, reindeer_ports):
        print(f"Reindeer sender: {reindeer_ports}")
        reindeer_ports_as_list = list(reindeer_ports)
        reindeer_ports_as_list.append(sender)

        buffer = bytearray()
        buffer.extend("R".encode())
        for port in reindeer_ports_as_list:
            buffer.extend(struct.pack("!I", port))

        send_message(sender, host, port, buffer)

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
        self._is_last_reindeer = False
        self._all_reindeer_awake = False


    replicated
    def setAllReindeerAwake(self, state):
        self._all_reindeer_awake = state
        return self._all_reindeer_awake
        

    def getAllReindeerAwake(self):
        return self._all_reindeer_awake


def run(reindeer_worker):
    print(f"Running reindeer worker {reindeer_worker.selfNode}")
    sleep_time = random.randint(1, 5)
    while True:
        time.sleep(0.5)
        leader = reindeer_worker._getLeader()

        if leader is None:
            continue
        
        try:

            if lock_manager.tryAcquire("reindeerLock", sync=True):
                if len(woke.rawData()) < NUM_REINDEER and not isWoke:
                    woke.append(
                        (reindeer_worker._extra_port, sleep_time),
                        callback=partial(
                            onNodeAppended, node=reindeer_worker.selfNode
                        ),
                    )

                    if len(woke.rawData()) + 1 == NUM_REINDEER:
                        # Find the reindeer with the longest sleep time.
                        # if two are the same, then it will return the first one in the arr. 
                        # The array is distrubted, meaning its the same for all processes!
                        last_awake_reindeer = max(woke.rawData(), key=lambda item: item[1])
                        print(f"Last awake reindeer: {last_awake_reindeer}")
                        
                        if reindeer_worker._extra_port == last_awake_reindeer[0]:

                            logger.info(f'I am the last reindeer to wake up with sleep time: {sleep_time} seconds')
                            reindeer_worker._is_last_reindeer = True
                            reindeer_worker.setAllReindeerAwake(True)
            
                # Release the lock
                lock_manager.release("reindeerLock")

                if reindeer_worker.getAllReindeerAwake():

                    print(f"Reindeer {reindeer_worker.selfNode} is awake!")

                    if reindeer_worker._is_last_reindeer:
                        print(f"Reindeer {reindeer_worker.selfNode} is the last reindeer to wake up!")
                        extra_ports = [node[0] for node in woke.rawData()]
                        runReindeerContacter(reindeer_worker._extra_port, extra_ports)

                        reindeer_worker._is_last_reindeer = False
                        reindeer_worker.setAllReindeerAwake(False)
                        woke.clear()
                    else:
                        print(f"Reindeer {reindeer_worker.selfNode} is NOT the last reindeer to wake up!")
                        runReindeerListener(reindeer_worker._extra_port)

        except Exception as e:
            logger.error(f"Could not acquire lock: {e}")
        finally:
            if lock_manager.isAcquired("reindeerLock"):
                lock_manager.release("reindeerLock")


def send_message(sender, host, port, buffer):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as conn_socket:
            conn_socket.connect((host, port))
            conn_socket.sendall(buffer)

    except ConnectionRefusedError:
        logger.exception(f"{sender} Couldn't connect to: {host}:{port}.")


def onNodeAppended(result, error, node):
    if error == FAIL_REASON.SUCCESS:
        global isWoke
        logger.info(f"ADDED - REQUEST [SUCCESS]: {node}, result: {result}")
        isWoke = True
    else:
        logger.error(f"ADDED - REQUEST [FAILED]: {node}, error: {error}, result: {result}")

def runReindeerContacter(port, reindeer_ports):
    ReinderContacter(port, reindeer_ports).run()

def runReindeerListener(port):
    ReinderContacter(port).listener(LOCAL_HOST, port)

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
    woke = ReplList()
    reindeer_worker = ReindeerWorker(
        node, otherNodes, consumers=[lock_manager, woke], extra_port=port + 1
    )
    run(reindeer_worker)
    
