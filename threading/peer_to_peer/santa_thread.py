import socket
import struct
import socketserver
import time
import threading

LOCAL_HOST = "127.0.0.1"
SANTA_PORT = 29800

def santa_threads(my_ip, my_port):
    class RequestHandler(socketserver.StreamRequestHandler):
        def handle(self):
            identifier = self.request.recv(1).decode() # Recieving the identifier

            if identifier == 'R': # Identifier is the Reindeer
                payload = self.request.recv(12) # Read the 12 bytes for the triple
                id, sleep_time, port = struct.unpack('!3I', payload)

                print(f"SL: - Recieved message: reindeer_id: {id}, sleep_time: {sleep_time}, port: {port}")
                print("Santa and the reindeer gets to work!")
                time.sleep(2) # Simulating santa working
                message = 'Go back on holiday, reindeer!'

                    
            elif identifier == 'E': #Identifier is the Elves
                
                self.request.recv(12)

                #print(f"SL: - Recieved message: elf_id: {id}, port: {port}")
                print("Santa goes to help the elves")
                time.sleep(2) # Simulating Santa helping elves
                message = 'Get back to work, elves!'


            # Writing back tom either the elves or reindeer
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as conn_socket:
                conn_socket.connect((LOCAL_HOST, port))

                # Send a string
                buffer = bytearray()
                buffer.append(1)  # Message type 1 = string
                buffer.extend(struct.pack('!I', len(message)))
                buffer.extend(bytes(message, 'utf-8'))
                conn_socket.sendall(buffer)

                    

    def listener():
        with socketserver.ThreadingTCPServer((my_ip, my_port), RequestHandler) as server:
            print(f"Santa -  Starting reindeer listener: {my_ip}:{my_port}")
            try:
                server.serve_forever()
            finally:
                server.server_close()

    sub_threads = [ threading.Thread(target=listener) ]

    for sub_thread in sub_threads:
        sub_thread.start()
    for sub_thread in sub_threads:
        sub_thread.join()

if __name__ == '__main__':
    santa_ip = LOCAL_HOST
    sant_port = SANTA_PORT
    
    santa_thread = threading.Thread(target=santa_threads, args=(santa_ip, sant_port))

    santa_thread.start()
    santa_thread.join()



