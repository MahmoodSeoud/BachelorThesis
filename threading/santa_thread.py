import socket
import struct
import socketserver
import time
import threading
import logging

LOCAL_HOST = "127.0.0.1"
SANTA_PORT = 29800
CHAIN_LEADER_PORT = 8888

logger = logging.getLogger(__name__)
logging.basicConfig(
    format="%(levelname)s %(asctime)s %(message)s",
    datefmt="%d/%m/%Y %H:%M:%S",
    encoding="utf-8",
    level=logging.DEBUG,
)

def santa_threads(my_ip, my_port):
    global reindeer_runs, elve_runs
    reindeer_runs = elve_runs = 0
    logger.info('timing starts')
    class RequestHandler(socketserver.StreamRequestHandler):
        def handle(self):
            identifier = self.request.recv(1).decode() # Recieving the identifier

            if identifier == 'R': # Identifier is the Reindeer
                print("Santa and the reindeer gets to work!")
                time.sleep(5) # Simulating santa working

                payload = self.request.recv(36) # Read the 36 bytes (9 * 4 bytes) address
                ports = struct.unpack('!9I', payload)
                message = 'Go back on holiday, reindeer!'

                buffer = bytearray()
                buffer.extend(message.encode('utf-8'))
                for port in ports:
                    send_message(f'Santa - {SANTA_PORT}', LOCAL_HOST, port, buffer)
                global reindeer_runs
                reindeer_runs += 1
                    
            elif identifier == 'E': #Identifier is the Elves
                print("Santa goes to help the elves")
                time.sleep(5) # Simulating Santa helping elves

                # Receive the message
                payload =  self.request.recv(12)
                recieved_chain = struct.unpack('!3I', payload)
                message = 'Get back to work, elves!'

                buffer = bytearray()
                buffer.extend(message.encode('utf-8'))
                for port in recieved_chain:
                    send_message(f'Santa - {SANTA_PORT}', LOCAL_HOST, port, buffer)
                global elve_runs
                elve_runs += 1

            if reindeer_runs == 10000:
                logger.info('Reindeer won')
            elif elve_runs == 10000:
                logger.info('Elves won')
                    
           
    def listener():
        with socketserver.ThreadingTCPServer((my_ip, my_port), RequestHandler) as server:
            print(f"Santa - Starting listener: {my_ip}:{my_port}")
            try:
                server.serve_forever()
            finally:
                server.server_close()

    def send_message(sender, host, port, buffer):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as conn_socket:
                conn_socket.connect((host, port))
                conn_socket.sendall(buffer)

        except ConnectionRefusedError:
            print(f"{sender} Couldn't connect to " f"{host}:{port}.")

    sub_threads = [ threading.Thread(target=listener) ]

    for sub_thread in sub_threads:
        sub_thread.start()
    for sub_thread in sub_threads:
        sub_thread.join()

if __name__ == '__main__':
    santa_ip = LOCAL_HOST
    santa_port = SANTA_PORT
    
    santa_thread = threading.Thread(target=santa_threads, args=(santa_ip, santa_port))

    santa_thread.start()
    santa_thread.join()



