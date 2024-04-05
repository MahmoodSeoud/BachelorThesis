import socket
import struct
import socketserver
import time
import threading
import pickle

LOCAL_HOST = "127.0.0.1"
SANTA_PORT = 29800
CHAIN_LEADER_PORT = 8888

def santa_threads(my_ip, my_port):
    class RequestHandler(socketserver.StreamRequestHandler):
        def handle(self):
            identifier = self.request.recv(1).decode() # Recieving the identifier

            if identifier == 'R': # Identifier is the Reindeer
                payload = self.request.recv(4) # Read the 12 bytes for the triple
                port = struct.unpack('!I', payload)[0]

                print("Santa and the reindeer gets to work!")
                time.sleep(5) # Simulating santa working

                # Send a string
                message = 'Go back on holiday, reindeer!'

                buffer = bytearray()
                buffer.append(1)  # Message type 1 = string
                buffer.extend(message.encode('utf-8'))
                
                send_message('Santa', LOCAL_HOST, port, buffer)
              

                    
            elif identifier == 'E': #Identifier is the Elves
                print("Santa goes to help the elves")
                time.sleep(5) # Simulating Santa helping elves

                # Receive the message
                payload =  self.request.recv(12)
                recieved_chain = struct.unpack('!3I', payload)

                message = 'Get back to work, elves!'

                buffer = bytearray()
                buffer.extend(message.encode('utf-8'))

                send_message('Santa', LOCAL_HOST, recieved_chain[0], buffer)
                send_message('Santa', LOCAL_HOST, recieved_chain[1], buffer)
                send_message('Santa', LOCAL_HOST, recieved_chain[2], buffer)
           


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
    sant_port = SANTA_PORT
    
    santa_thread = threading.Thread(target=santa_threads, args=(santa_ip, sant_port))

    santa_thread.start()
    santa_thread.join()



