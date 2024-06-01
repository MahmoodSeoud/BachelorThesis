import socket
import struct
import socketserver
import time
import logging

LOCAL_HOST = "127.0.0.1"
SANTA_PORT = 29800
CHAIN_LEADER_PORT = 8888
LOGFILE = "./log/unix/santa/santa.txt"

logger = logging.getLogger(__name__)
logging.basicConfig(
    format="%(levelname)s %(asctime)s %(message)s",
    datefmt="%d/%m/%Y %H:%M:%S",
    encoding="utf-8",
    level=logging.DEBUG,
    filename=LOGFILE,
    filemode="w",
)

system_runs = reindeer_runs = elve_runs = 0
milestone = 100
endGoal = 1000


class ThreadedSantaTCPRequestHandler(socketserver.StreamRequestHandler):

    def handle(self):
        identifier = self.request.recv(1).decode()  # Recieving the identifier

        if identifier == "R":  # Identifier is the Reindeer
            self.handle_reindeer_request()
        elif identifier == "E":  # Identifier is the Elves
            self.handle_elf_request()

        global system_runs
        system_runs += 1

        if system_runs % milestone == 0:
            logger.info(f"System reached {system_runs} runs")

    def handle_reindeer_request(self):
        logger.info("Santa and the reindeer gets to work!")
        ## Removed the sleep for testing purposes
        # time.sleep(5) # Simulating santa working

        payload = self.request.recv(40)  # Read the 4 bytes + 36 bytes (9 * 4 bytes) address
        amount_of_nodes = struct.unpack("!I", payload[:4])[0] # amount of nodes to contact
        print(f"Amount of nodes: {amount_of_nodes}")
        ports = struct.unpack(f"!{amount_of_nodes}I", payload[4:4+4*amount_of_nodes])
        message = "Go back on holiday, reindeer!"

        buffer = bytearray()
        buffer.extend(message.encode("utf-8"))
        for port in ports:
            self.send_message(LOCAL_HOST, port, buffer)

        # global reindeer_runs
        # reindeer_runs += 1

        # Check for milestones for reindeer
        # if reindeer_runs % milestone == 0:
        #    logger.info(f'Reindeer reached {reindeer_runs} runs')

    def handle_elf_request(self):
        logger.info("Santa goes to help the elves")
        ## Removed the sleep for testing purposes
        # time.sleep(5) # Simulating Santa helping elves

        # Receive the message
        payload = self.request.recv(12)
        recieved_chain = struct.unpack("!3I", payload)
        message = "Get back to work, elves!"

        buffer = bytearray()
        buffer.extend(message.encode("utf-8"))
        for port in recieved_chain:
            print(f"Port: {port}")
            self.send_message(LOCAL_HOST, port, buffer)

        global elve_runs
        elve_runs += 1

        # Check for milestones for elves
        # if elve_runs % milestone == 0:
        #   logger.info(f'Elves reached {elve_runs} runs')

    def send_message(self, host, port, buffer, timeout=30):
        start_time = time.time()
        while True:
            try:
                logger.info(f"Sending message to {host}:{port}.")
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as conn_socket:
                    print(f"Connecting to host:{host}:port{port}")
                    conn_socket.connect((host, port))
                    conn_socket.sendall(buffer)
                break  # If the message is sent successfully, break the loop

            except ConnectionRefusedError:
                logger.exception(f"Couldn't connect to {host}:{port}.")
                if time.time() - start_time > timeout:
                    logger.error(
                        f"Timeout after {timeout} seconds while trying to send message to {host}:{port}."
                    )
                    break  # If timeout has passed, break the loop
                time.sleep(1)  # Wait for a second before trying again)


if __name__ == "__main__":
    logger.info("Timing Starts")

    with socketserver.ThreadingTCPServer(
        (LOCAL_HOST, SANTA_PORT), ThreadedSantaTCPRequestHandler
    ) as server:
        logger.info(f"Santa - Starting listener: {LOCAL_HOST}:{SANTA_PORT}")
        try:
            server.serve_forever()
        finally:
            server.server_close()
