import sys
import threading
import socketserver
import socket
import time
import struct
import logging
import random
from functools import partial
from pysyncobj import SyncObj, SyncObjConf, FAIL_REASON
from pysyncobj.batteries import ReplLockManager, ReplSet

LOCAL_HOST = "127.0.0.1"
SANTA_PORT = 29800
LOGFILE = sys.argv[1]
NUM_CHAIN_MEMBERS = 3

logger = logging.getLogger(__name__)
logging.basicConfig(
    format="%(levelname)s %(asctime)s %(message)s",
    datefmt="%d/%m/%Y %H:%M:%S",
    filename=LOGFILE,
    filemode="w",
    encoding="utf-8",
    level=logging.DEBUG,
)


class ElfContacter:
    def __init__(self, sender, local_chain_members=None):
        self.sender = sender
        self.local_chain_members = local_chain_members

    # Class for handling the connection between the elves and Santa
    class RequestHandler(socketserver.StreamRequestHandler):
        
        def handle(self):
            data = self.request.recv(1024)
            message = data.decode("utf-8")
            logger.info(f"[CHAIN CLUSTER] Received a message: {message}")
            print(f"Received a message: {message}")
        
        def handle_timeout(self):
            logger.info(f"[CHAIN CLUSTER] Timeout on connection")
            print("Timeout on connection")

    def listener(self, host, port):
        
        server = socketserver.ThreadingTCPServer(
            (LOCAL_HOST, port),
            self.RequestHandler,
        )
        server.timeout = 10

        with server:
            logger.info(f"[{self.sender}] - Starting listener: ({host}:{port})")
            try:
                server.handle_request()  # Server will handle the request from Santa and then close
            finally:
                server.server_close()

    def contact_santa(self, sender, targetHost, targetPort, chain):

        chain_as_list = chain
        chain_as_list.append(sender)

        buffer = bytearray()
        buffer.extend("E".encode())
        for port in chain_as_list:
            buffer.extend(struct.pack("!I", port))

        send_message(sender, targetHost, targetPort, buffer)

    def start_threads(self):
        sub_threads = [
            threading.Thread(target=self.listener, args=(LOCAL_HOST, self.sender)),
            threading.Thread(
                target=self.contact_santa,
                args=(self.sender, LOCAL_HOST, SANTA_PORT, self.local_chain_members),
            ),
        ]

        for sub_thread in sub_threads:
            sub_thread.start()

        for sub_thread in sub_threads:
            sub_thread.join()

    def run(self):
        self.start_threads()


class ElfWorker(SyncObj):
    def __init__(
        self, node, otherNodes, consumers, extra_port, local_chain_members=None
    ):
        super(ElfWorker, self).__init__(
            node,
            otherNodes,
            consumers=consumers,
            conf=SyncObjConf(
                connectionRetryTime=10.0,
            ),
        )

        self._is_in_chain = False
        self._extra_port = extra_port
        self._local_chain_members = local_chain_members


def runElfContacter(port, chainMembers):
    ElfContacter(port, chainMembers).run()


def runElfListener(port):
    ElfContacter(port).listener(LOCAL_HOST, port)


def onNodeAdded(result, error, node, cluster):
    if error == FAIL_REASON.SUCCESS:
        logger.info(
            f"ADDED - REQUEST [SUCCESS]: {node} - CLUSTER: {cluster} - result: {result}"
        )
    else:
        logger.error(
            f"ADDED - REQUEST [FAIL]: {node} - CLUSTER: {cluster} - result: {result}"
        )


def send_message(sender, targetHost, targetPort, buffer):
    print(f"Sending message to {targetHost}:{targetPort}")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as conn_socket:
            conn_socket.connect((targetHost, targetPort))
            conn_socket.sendall(buffer)

    except ConnectionRefusedError:
        logger.exception(f"{sender} Couldn't connect to: {targetHost}:{port}.")


def run(elf_worker):
    print(f"Running elf worker {elf_worker.selfNode}")
    print(f"Extra port: {elf_worker._extra_port}")

    while True:

        if not elf_worker.isReady():
            continue

        # Check if there's a leader, if not, continue waiting
        leader = elf_worker._getLeader()
        if leader is None:
            continue

        ## Removed the randomsleep for testing purposes
        sleep_time = random.randint(1, 5)
        #time.sleep(sleep_time)

        
        try:
            # Attempt to acquire the lock
            if lock_manager.tryAcquire("chainLock", sync=True):
                logger.info("Acquired lock")
                # Check if the chain is eligible for modification
                if len(chain.rawData()) < NUM_CHAIN_MEMBERS and not elf_worker._is_in_chain:
                    # Add elf_worker to the chain if it's not full and elf_worker is not already in it
                    chain.add(
                        (elf_worker._extra_port, elf_worker.selfNode),
                        callback=partial(
                            onNodeAdded, node=elf_worker.selfNode, cluster="chain"
                        ),
                    )

                    # Plus one because the the effect might not be immediate
                    if len(chain.rawData()) + 1 == NUM_CHAIN_MEMBERS:
                        elf_worker._local_chain_members = chain.rawData()
                        chain.clear()

                # Release the lock
                logger.info("Releasing lock")
                lock_manager.release("chainLock")

                elf_worker._is_in_chain = True

                # This is within the lock because we want to make sure that the chain is not modified
                if elf_worker._is_in_chain:

                    if elf_worker._local_chain_members is not None:
                        otherChainMemberExtraPort = [
                            x[0] for x in elf_worker._local_chain_members
                        ]
                        otherChainMemberSelfNode = [
                            x[1] for x in elf_worker._local_chain_members
                        ]
                        connected_members = [
                            x
                            for x in otherChainMemberSelfNode
                            if elf_worker.isNodeConnected(x)
                        ]

                    #  # Disonnect test -- PLEASE REMOVE WHEN DONE --  
                        #if elf_worker._extra_port == 8001 or elf_worker._extra_port == 8003 or elf_worker._extra_port == 8005 or elf_worker._extra_port == 8007:
                        #    print("Disconnecting", elf_worker._extra_port)
                        #    sys.exit(1)
                        
                        # Check if there are two connected members
                        if len(connected_members) == 2:
                            runElfContacter(
                                elf_worker._extra_port, otherChainMemberExtraPort
                            )
                        else:
                            print("Please restart the chain")
                            # Message the other guys it's time to restart
                            for member in connected_members:
                                send_message(
                                    "Elf",
                                    member.host,
                                    member.port + 1, # TODO: Make this explixtly the extra port
                                    bytearray("Restart!", "utf-8"),
                                )

                        elf_worker._local_chain_members = None

                    else:
                        runElfListener(elf_worker._extra_port)
                        
                    elf_worker._is_in_chain = False

        except Exception as e:
            logger.exception(f"Error in main: {e}")
        finally:
            if lock_manager.isAcquired("chainLock"):
                logger.info("Releasing lock")
                lock_manager.release("chainLock")


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
    lock_manager = ReplLockManager(autoUnlockTime=10.0)
    chain = ReplSet()
    elf_worker = ElfWorker(
        node, otherNodes, consumers=[lock_manager, chain], extra_port=port + 1
    )
    run(elf_worker)