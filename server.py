import socket
import psycopg2
import threading

HOST = "127.0.0.1"
PORT = 28752
clients = {}

def on_new_client(conn, addr):
     with conn:
        print(f"Connected by {addr}")
        username = conn.recv(1024).decode().strip()
        clients[username] = (conn, addr)
        while True:
            data = conn.recv(1024)
            if not data:
                print(f"Client '{username}' at {addr} disconnected.")
                break
            message = data.decode().strip()
            print(f"Data from {username}: {message}")
            broadcast_message = f"{username}: {message}"
            for target_username, (target_conn, _) in clients.items():
                if target_conn != conn:
                    try:
                        target_conn.sendall(broadcast_message.encode())
                    except:
                        print(f"Failed to send message to {target_username}")
         # Cleanup on disconnect
        del clients[username]
        print(f"Removed client {username} ({addr}) from clients list.")




def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((HOST, PORT))
    while True:
        s.listen()
        try:
            conn, addr = s.accept()
            thread = threading.Thread(target=on_new_client, args=(conn,addr, ))
            thread.start()
        except:
            s.close()
   
main()
