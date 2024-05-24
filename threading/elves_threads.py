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
from pysyncobj.tcp_connection import CONNECTION_STATE
from pysyncobj.batteries import ReplLockManager, ReplSet

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


class ElfContacter:
    def __init__(self, sender, local_chain_members=None):
        self.sender = sender
        self.local_chain_members = local_chain_members

    # Class for handling the connection between the elves and Santa
    class RequestHandler(socketserver.StreamRequestHandler):
        def handle(self):
            self.request.settimeout(10)  # Set the timout for the connection
            data = self.request.recv(1024)
            message = data.decode("utf-8")
            logger.info(f"[CHAIN CLUSTER] Received a message from Santa: {message}")

    def listener(self, host, port):
        with socketserver.ThreadingTCPServer(
            (host, port), self.RequestHandler
        ) as server:
            logger.info(f"[{self.sender}] - Starting listener: ({host}:{port})")
            try:
                server.handle_request()  # Server will handle the request from Santa and then close
            finally:
                server.server_close()

    def contact_santa(self, sender, targetHost, targetPort, chain):
        chain_as_list = map(lambda x: x[0], chain)
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
                dynamicMembershipChange=True,
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
        sleep_time = random.randint(1, 5)
        time.sleep(sleep_time)

        # Check if there's a leader, if not, continue waiting
        leader = elf_worker._getLeader()
        if leader is None:
            continue
        try:
            # Attempt to acquire the lock
            if lock_manager.tryAcquire("chainLock", sync=True):

                # Check if the chain is eligible for modification
                if len(chain.rawData()) < 3:
                    # Add elf_worker to the chain if it's not full and elf_worker is not already in it
                    chain.add(
                        (elf_worker._extra_port, elf_worker.selfNode),
                        callback=partial(
                            onNodeAdded, node=elf_worker.selfNode, cluster="chain"
                        ),
                    )
                    elf_worker._is_in_chain = True

                    # Plus one because the the effect might not be immediate
                    if len(chain.rawData()) + 1 == 3:
                        elf_worker._local_chain_members = chain.rawData()
                        chain.clear()

                # Release the lock
                lock_manager.release("chainLock")

                if elf_worker._is_in_chain:
                    if elf_worker._local_chain_members is None :
                        runElfListener(elf_worker._extra_port)
                        elf_worker._is_in_chain = False
                    else:
                        print(f'CHAIN IS:', elf_worker._local_chain_members)
                        chain_member_one_status = elf_worker.getState()[f'partner_node_status_server_localhost:{elf_worker._local_chain_members[0]}']
                        chain_member_two_status = elf_worker.getState()[f'partner_node_status_server_localhost:{elf_worker._local_chain_members[1]}']
                        print(f'CHAIN MEMBER ONE STATUS:', chain_member_one_status)
                        print(f'CHAIN MEMBER TWO STATUS:', chain_member_two_status)
                        if True:
                            runElfContacter(
                                elf_worker._extra_port, elf_worker._local_chain_members
                            )
                            elf_worker._local_chain_members = None
                            elf_worker._is_in_chain = False

        except Exception as e:
            logger.error(f"Could not acquire lock: {e}")
        finally:
            if lock_manager.isAcquired("chainLock"):
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
    lock_manager = ReplLockManager(autoUnlockTime=75.0)
    chain = ReplSet()
    elf_worker = ElfWorker(
        node, otherNodes, consumers=[lock_manager, chain], extra_port=port + 1
    )
    run(elf_worker)
