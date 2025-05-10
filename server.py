import socket
import pyodbc
import threading

HOST = "0.0.0.0"
PORT = 28752
clients = {}
clients_lock = threading.Lock()

server = 'tcp:quackmsg.database.windows.net,1433'
database = 'messagedb'
username = 'noah'
password = '9aie7Hgslc*9Wp'
connectionString = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={SERVER};DATABASE={DATABASE};UID={USERNAME};PWD={PASSWORD}'

try:
    db = pyodbc.connect(connectionStringimport)
    print("Connection successful!")
except Exception as e:
    print("Error connecting to SQL Server.")
    print(e)

logins = {"Noah": {'password': "$2b$12$Dhd2UJY4dktY4gfQ.3cQG.L1gxBPdbvcCatTibDimYLDq2HkId5ni", 'salt':"$2b$12$Dhd2UJY4dktY4gfQ.3cQG."}, "dad": {'password': "$2b$12$gFMcOWz0uGijshZNO5TZvewUIOJ8HahWG63bJmLqW7kDk.PNDMbGK", 'salt':"$2b$12$gFMcOWz0uGijshZNO5TZve"}}

def on_new_client(conn, addr):
     with conn:
        print(f"Connected by {addr}")
        # Recive inital instuction (create user or login)
        data = conn.recv(1024).decode().strip()
        if data == 'newaccount':
            create_user(conn, addr)
        else:
            login(conn, addr)
        # Add to clients list
        with clients_lock:
            clients[username] = (conn, addr)
        # Recive messages and send to all clients
        client_run(conn, addr, username)
        # Cleanup on disconnect
        with clients_lock:
            del clients[username]
        print(f"Removed client {username} ({addr}) from clients list.")

def login(conn, addr):
     while True:
        username_sent = conn.recv(1024).decode().strip()
        if username_sent in logins:
            print(f"Username {username_sent} found")
            username = username_sent
            conn.sendall(logins[username]['salt'].encode())
            password_hashed = conn.recv(1042).decode().strip()
            if password_hashed == logins[username]['password']:
                conn.sendall(b'1')
                break
            else:
                conn.sendall(b'0')
                continue
        if username_sent == "\0":
            break
        else:
            conn.sendall(str(False).encode())
            continue

def create_user(conn, addr):
    while True:
        username_sent = conn.recv(1024).decode().strip()
        if username not in logins:
            conn.sendall(b'0')
            password_hashed = conn.recv(1024).decode().strip()
            salt = conn.recv(1024).decode().strip()
            logins[username] = {'password': password_hashed, 'salt': salt}
            conn.sendall(b'1')




def client_run(conn, addr, username):
    while True:
        data = conn.recv(1024)
        if not data:
            print(f"Client '{username}' at {addr} disconnected.")
            break
        message = data.decode().strip()
        print(f"Data from {username}: {message}")
        broadcast_message = f"{username}: {message}"
        for target_username, (target_conn, _) in clients.copy().items():
            if target_conn != conn:
                try:
                    target_conn.sendall(broadcast_message.encode())
                except:
                    print(f"Failed to send message to {target_username}")
 


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
if __name__ == "__main__":   
    main()
