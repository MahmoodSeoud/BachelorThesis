import socket
import socketserver
import struct
import threading
import time
import random

NUM_REINDEER = 9
LOCAL_HOST = "127.0.0.1"
SANTA_PORT = 29800

def threaded_reindeer(reindeer_id, 
                    my_ip,
                    my_port,
                    peer_ports,
                    lock,
                    cond
                    ):

    woke = []
    class RequestHandler(socketserver.StreamRequestHandler):
        def handle(self):
            
            # Receive the message type
            message_type = self.request.recv(1)[0]

            if message_type == 1: # Handle a string message from Santa
                # Receive the length of the string (4 bytes for an unsigned integer)
                request_header = self.request.recv(4)
                request_length = struct.unpack('!I', request_header)[0]
                payload = self.request.recv(request_length)
                print(f"Last reindeer - Recieved message: {payload.decode('ascii')}")


                # Print line to indicicate new cycle
                print('--------------------------')
                # Notify all reindeer that it's time to go on holiday (sleep)
                with cond:
                    cond.notify_all()


            elif message_type == 2:  # Handle a tuple message from other reindeer
                data = self.request.recv(12)
                id, sleep_time, port = struct.unpack('!3I', data)

                #print(f"RL: {reindeer_id} - Recieved message: reindeer_id: {id}, sleep_time: {sleep_time}")
                
                with lock:
                    if len(woke) < NUM_REINDEER:
                        reindeer_entry = { "id": id, "sleep_time": sleep_time, "port": port }   
                        woke.append(reindeer_entry)

                    if len(woke) == NUM_REINDEER:
                        last_reindeer = max(woke, key=lambda item: (item['sleep_time'], item['id']))
                        #print(f"RL {reindeer_id} - I think this is the last ",last_reindeer)

                        # No reindeer are awake anymore
                        woke.clear()

                        if reindeer_id == last_reindeer['id']:
                            santa_writer(last_reindeer)

    def reindeer_listener():
        # Start server side
        with socketserver.ThreadingTCPServer((my_ip, my_port), RequestHandler) as server:
            print(f"RL: {reindeer_id} -  Starting reindeer listener: {my_ip}:{my_port}")
            try: 
                server.serve_forever()
            finally:
                server.server_close()

    def reindeer_writer():

        while True:
            sleep_time = random.randint(1,5)
            time.sleep(sleep_time)
            print(f'Reindeer {reindeer_id} woke up after {sleep_time} seconds')
            for peer_port in peer_ports:
                try:
                   #print(f"RW: {reindeer_id} -  Connecting to reindeer at: " f"{LOCAL_HOST}:{peer_port}")
                        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as conn_socket:
                            conn_socket.connect((LOCAL_HOST, peer_port))

                            buffer = bytearray()
                            buffer.append(2) # Message type 2 = pair of integers
                            buffer.extend(struct.pack('!3I', reindeer_id, sleep_time, my_port))
                            conn_socket.sendall(buffer)

                except ConnectionRefusedError:
                    print(f"RW {reindeer_id} - Couldn't connect to " f"{my_ip}:{peer_port}. Will try again in 3 seconds.")

            # Waiting for all the threads to sync
            with cond:
                cond.wait()

    
    def santa_writer(last_reindeer):
        print(f"last reindeer to wake up was {last_reindeer['id']} after {last_reindeer['sleep_time']} seconds")
        
        # Sent msg to Santa whom then msg's back here so that we can notify_all()
        try:
            print(f"Last reindeer: {last_reindeer['id']} -  Connecting to Santa at: " f"{LOCAL_HOST}:{SANTA_PORT}")
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as conn_socket:

                conn_socket.connect((LOCAL_HOST, SANTA_PORT))

                identifier = 'R'
                buffer = bytearray()
                buffer.extend(identifier.encode())
                buffer.extend(struct.pack('!3I', last_reindeer['id'], last_reindeer['sleep_time'], last_reindeer['port']))
                conn_socket.sendall(buffer)

        except ConnectionRefusedError:
            print(f"Last reindeer - Couldn't connect to " f"{LOCAL_HOST}:{SANTA_PORT}.")

    

    sub_threads = [
        threading.Thread(target=reindeer_listener),
        threading.Thread(target=reindeer_writer)
    ]

    for sub_thread in sub_threads:
        sub_thread.start()

    for sub_thread in sub_threads:
        sub_thread.join()

if __name__ == "__main__":

    peer_addresses = [(LOCAL_HOST, 4000 + i) for i in range(0, NUM_REINDEER)]

    lock = threading.Lock()
    condition = threading.Condition()

    # Starting one reindeer thread
    reindeer_threads = [
        threading.Thread(
        target=threaded_reindeer, 
        args=(
            i+1, 
              peer_addresses[i][0],
               peer_addresses[i][1], 
               [port for ip, port in peer_addresses],
               lock,
               condition,
              ), 
        daemon=True
    ) for i in range(0, NUM_REINDEER)]

    for reindeer_thread in reindeer_threads:
        reindeer_thread.start()

    for reindeer_thread in reindeer_threads:
        reindeer_thread.join()

