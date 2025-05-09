import socket
import psycopg2

HOST = "127.0.0.1"
PORT = 28752

def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((HOST, PORT))
    s.listen()
    conn, addr = s.accept()

    with conn:
        print(f"Connected by {addr}")
        while True:
            data = conn.recv(1024)
            if not data:
                break
            print(f"Data from client: {data.decode().strip()}")
            conn.sendall(data)

main()
