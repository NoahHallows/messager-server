import socket
import pyodbc
import threading
import bcrypt
import time
import sys
import select
import json
import struct
import os


HOST = "0.0.0.0"
#PORT = 23456
PORT = 28752
clients = {}
clients_lock = threading.Lock()

VERSION = 1.0

SERVER = 'tcp:quackmsg.database.windows.net,1433'
DATABASE = 'messagedb'
USERNAME = os.environ['SQL_USERNAME']
PASSWORD = os.environ['SQL_PASSWORD']
connectionString = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={SERVER};DATABASE={DATABASE};UID={USERNAME};PWD={PASSWORD}'

try:
    db = pyodbc.connect(connectionString)
    cursor = db.cursor()
    print("Connection successful!")
except Exception as e:
    print("Error connecting to SQL Server.")
    print(e)


def send_past_messages(conn, addr, username):
    try:
        SQL_STATEMENT = "SELECT * FROM MESSAGES WHERE sender = ? OR receiver = ? OR receiver = 'all';"
        cursor.execute(SQL_STATEMENT, (username, username))
        rows = cursor.fetchall()
        for row in rows:
            id, sender, receiver, message, timestamp = row
            payload = {'sender': sender, 'message':message}
            data = json.dumps(payload).encode("utf-8")
            header = struct.pack("!I", len(data))
            conn.sendall(header + data)
    except Exception as e:
        print(f"error sending past messages: {e}")


def on_new_client(conn, addr):
    try:
        with conn:
            print(f"Connected by {addr}")
            conn.sendall(VERSION.encode())
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
            
            payload = {"sender": "Server", "message": "Welcome to quackmessage"}
            data = json.dumps(payload).encode("utf-8")
            header = struct.pack("!I", len(data))
            conn.sendall(header + data)
            
            send_past_messages(conn, addr, username)

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
            SQL_STATEMENT = "SELECT salt FROM USERS WHERE username = ?;"
            cursor.execute(SQL_STATEMENT, username)
            row = cursor.fetchone()
            salt = row[0]
            conn.sendall(salt)
            password_to_check = conn.recv(1042).strip()
            SQL_STATEMENT = "SELECT password_hashed FROM USERS WHERE username = ?;"
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
        result = recv_message(conn)
        if result is None:
            break
        sender, message = result
        if (sender != username):
            print(f"Username, {username}, and sender, {sender} don't match.")
            continue
        payload = {"sender": username, "message": message}
        broadcast_payload = json.dumps(payload).encode("utf-8")
        # 3) prefix with 4-byte big-endian length
        header = struct.pack("!I", len(broadcast_payload))
        cursor.execute("INSERT INTO MESSAGES (sender, receiver, message) VALUES (?, ?, ?)", username, "all", message)
        db.commit()
        print(f"{username}: {message}")
        print(f"Payload: {broadcast_payload}")
        for target_username, (target_conn, _) in clients.copy().items():
            if target_conn != conn:
                try:
                    target_conn.sendall(header + broadcast_payload)
                    print(f"Sent message to: {target_username}")
                except:
                    print(f"Failed to send message to {target_username}")
 
def recv_message(conn):
    # 1) read exactly 4 bytes for length
    raw_len = conn.recv(4)
    if not raw_len:
        return None
    msg_len = struct.unpack("!I", raw_len)[0]

    # 2) read the JSON payload
    data = b""
    while len(data) < msg_len:
        chunk = conn.recv(msg_len - len(data))
        if not chunk:
            raise ConnectionError("client disconnected")
        data += chunk

    # 3) parse JSON
    payload = json.loads(data.decode("utf-8"))
    sender  = payload["sender"]
    message = payload["message"]
    return sender, message

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
    cursor.close()
    conn.close()
    s.close()

if __name__ == "__main__":   
    main()
