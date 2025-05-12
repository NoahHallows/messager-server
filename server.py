import socket
import pyodbc
import threading
import bcrypt
import time
import sys
import select

HOST = "0.0.0.0"
#PORT = 23456
PORT = 28752
clients = {}
clients_lock = threading.Lock()

SERVER = 'tcp:quackmsg.database.windows.net,1433'
DATABASE = 'messagedb'
USERNAME = 'noah'
PASSWORD = '9aie7Hgslc*9Wp'
connectionString = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={SERVER};DATABASE={DATABASE};UID={USERNAME};PWD={PASSWORD}'

try:
    db = pyodbc.connect(connectionString)
    cursor = db.cursor()
    print("Connection successful!")
except Exception as e:
    print("Error connecting to SQL Server.")
    print(e)


def on_new_client(conn, addr):
    try:
        with conn:
            print(f"Connected by {addr}")
            # Recive inital instuction (create user or login)
            data = conn.recv(1024)
            username_sent = conn.recv(1024).decode().strip()
            print(f"Username = {username_sent}")
            data = data.decode().strip()
            if data == 'newaccount':
                username = create_user(conn, addr, username_sent)
            else:
                username = login(conn, addr, username_sent)
            # Add to clients list
            with clients_lock:
                clients[username] = (conn, addr)
            # Recive messages and send to all clients
            client_run(conn, addr, username)
            # Cleanup on disconnect
            with clients_lock:
                del clients[username]
            print(f"Removed client {username} ({addr}) from clients list.")
    except Exception as e:
        print(f"An error occured with client {addr}: {e}")

def login(conn, addr, username_sent):
     while True:
        SQL_STATEMENT = "SELECT 1 FROM USERS WHERE username = ?;"
        cursor.execute(SQL_STATEMENT, username_sent)
        row = cursor.fetchone()
        if row:
            username = username_sent
            SQL_STATEMENT = "SELECT password_hashed FROM USERS WHERE username = ?;"
            cursor.execute(SQL_STATEMENT, username)
            row = cursor.fetchone()
            salt = row[0]
            conn.sendall(salt)
            password_to_check = conn.recv(1042).strip()
            SQL_STATEMENT = "SELECT password_hashed FROM USERS WHERE Username = ?;"
            cursor.execute(SQL_STATEMENT, username)
            row = cursor.fetchone()
            hashed_password = row[0]
            if password_to_check == hashed_password:
                conn.sendall(b'1')
                return username
            else:
                conn.sendall(b'0')
                continue
        else:
            conn.sendall(str(False).encode())
            continue

def create_user(conn, addr, username_sent):
    while True:
        SQL_STATEMENT = "SELECT 1 FROM USERS WHERE username = ?;"
        username_exist = cursor.execute(SQL_STATEMENT, username_sent)
        if username_exist != 1:
            conn.sendall(b'0')
            password_hashed = conn.recv(1024).strip()
            salt = conn.recv(62).strip()
            print(f"Username: {username_sent}, password hash: {password_hashed}, salt: {salt}")
            SQL_STATEMENT = "INSERT INTO USERS (username, password_hashed, salt) VALUES (?, ?, ?)"
            cursor.execute(SQL_STATEMENT, username_sent, password_hashed, salt)
            db.commit()
            conn.sendall(b'1')
            return username_sent
        else:
            continue




def client_run(conn, addr, username):
    while True:
        data = conn.recv(1024)
        if not data:
            print(f"Client '{username}' at {addr} disconnected.")
            break
        message = data.decode().strip()
        cursor.execute("INSERT INTO MESSAGES (sender, reciver, message) VALUES (?, ?, ?)", username, "all", message)
        db.commit()
        print(f"{username}: {message}")
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
        # Check if there's input available
        if select.select([sys.stdin], [], [], 0)[0]:
            user_input = sys.stdin.readline().strip()
            print(f"Received: {user_input}")
            if user_input == ":q":
                print("Exiting loop.")
                break
    cursor.close()
    conn.close()
    s.close()

if __name__ == "__main__":   
    main()
