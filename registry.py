from socket import *
import threading
import select
import logging
import database


class ClientThread(threading.Thread):
    def __init__(self, host, port, tcpClientSocket):
        threading.Thread.__init__(self)
        # host, port, socket of connected peer
        self.host = host
        self.port = port
        self.tcpClientSocket = tcpClientSocket

        # username, online status, udp server of connected peer
        self.username = None
        self.isOnline = True
        self.udpServer = None
        print("New thread started for {} : {}".format(self.host, self.port))

    # main of peer thread
    def run(self):
        self.lock = threading.Lock()
        print("Connection from: {} : {}".format(self.host, self.port))

        while True:
            try:
                message_bytes = self.tcpClientSocket.recv(1024)
                if message_bytes == b"":
                    break
                message_str = message_bytes.decode("utf-8")
                message = message_str.split("\n")

                # Log the received message for debugging or tracking purposes
                logging.info(
                    "Received from {} : {} -> {}".format(self.host, self.port, message)
                )

                # Register
                if message[0] == "register-request":
                    self.register(message[1], message[2])

                # Login
                elif message[0] == "login-request":
                    self.login(message[1], message[2], message[3])

                # Logout
                elif message[0] == "logout":
                    self.logout()
                    break

                # Search
                elif message[0] == "search-request":
                    self.search(message[1])

            except OSError as oErr:
                logging.error("OSError: {0}".format(oErr))
                break

    def register(self, username, password):
        if db.is_account_exist(username):
            response = "register-username-exist"
        else:
            db.register(username, password)
            response = "register-success"

        logging.info("Send to {} : {} -> {}".format(self.host, self.port, response))
        self.tcpClientSocket.send(response.encode())

    def login(self, username, password, port):
        if not db.is_account_exist(username):
            response = "login-fail"

        elif db.is_account_online(username):
            response = "login-user-online"

        else:
            retrievedPass = db.get_password(username)

            if retrievedPass == password:
                self.username = username
                self.lock.acquire()
                try:
                    tcpThreads[self.username] = self
                finally:
                    self.lock.release()

                db.user_login(username, self.host, port)
                response = "login-success"
                self.udpServer = UDPServer(self.username, self.tcpClientSocket)
                self.udpServer.start()
                self.udpServer.timer.start()

            else:
                response = "login-fail"

        logging.info("Send to {} : {} -> {}".format(self.host, self.port, response))
        self.tcpClientSocket.send(response.encode())

    def logout(self):
        if db.is_account_online(self.username):
            db.user_logout(self.username)
        self.lock.acquire()
        try:
            if self.username in tcpThreads:
                del tcpThreads[self.username]
        finally:
            self.lock.release()
            print("{} is logged out".format(self.username))
            self.tcpClientSocket.close()
            if self.udpServer is not None:
                self.udpServer.timer.cancel()

    def search(self, username):
        if db.is_account_exist(username):
            if db.is_account_online(username):
                peer_info = db.get_peer_ip_port(username)

                if peer_info:
                    response = "search-success\n{}\n{}".format(
                        peer_info[0], peer_info[1]
                    )
                else:
                    response = "search-not-online"

            else:
                response = "search-not-online"

        # enters if username does not exist
        else:
            response = "search-not-found"

        self.tcpClientSocket.send(response.encode())
        logging.info("Send to {} : {} -> {}".format(self.host, self.port, response))


# implementation of the udp server thread for clients
class UDPServer(threading.Thread):
    # udp server thread initializations
    def __init__(self, username, clientSocket):
        threading.Thread.__init__(self)
        self.username = username
        # timer thread for the udp server is initialized
        self.timer = threading.Timer(3, self.waitHelloMessage)
        self.tcpClientSocket = clientSocket

    # if hello message is not received before timeout
    # then peer is disconnected
    def waitHelloMessage(self):
        if self.username is not None:
            db.user_logout(self.username)
            if self.username in tcpThreads:
                del tcpThreads[self.username]
        self.tcpClientSocket.close()
        print("Removed {} from online peers".format(self.username))

    # resets the timer for udp server
    def resetTimer(self):
        self.timer.cancel()
        self.timer = threading.Timer(3, self.waitHelloMessage)
        self.timer.start()


# server port initialization
print("Registy started...")
port = 15600
portUDP = 15500

# db initialization
db = database.DB()

# gets the ip address of this peer
hostname = gethostname()
host = gethostbyname(hostname)
print("Registry IP address: {}".format(host))
print("Registry port number: {}".format(port))

# threads for active connections
tcpThreads = {}

# socket initialization
tcpSocket = socket(AF_INET, SOCK_STREAM)
tcpSocket.bind((host, port))
tcpSocket.listen(5)
udpSocket = socket(AF_INET, SOCK_DGRAM)
udpSocket.bind((host, portUDP))
inputs = [tcpSocket, udpSocket]

# log file initialization
logging.basicConfig(filename="registry.log", level=logging.INFO, filemode="w")


print("Listening for incoming connections...")
# as long as at least a socket exists to listen to, the registry runs
while tcpSocket:
    readable, writable, exceptional = select.select(inputs, [], [])

    # monitors for the incoming connections
    for sock in readable:
        # if the message received comes to the tcp socket, accept connection & start thread
        if sock is tcpSocket:
            tcpClientSocket, addr = tcpSocket.accept()
            newThread = ClientThread(addr[0], addr[1], tcpClientSocket)
            newThread.start()

        # if the message received comes to the udp socket, check hello
        elif sock is udpSocket:
            message, clientAddress = sock.recvfrom(1024)
            message = message.decode().split("\n")
            logging.info(
                "Received from {} : {} -> {}".format(
                    clientAddress[0], clientAddress[1], message
                )
            )

            # checks if it is a hello message
            if message[0] == "hello":
                # checks if the account that sent this hello message is online
                if message[1] in tcpThreads:
                    # resets the timeout for that peer
                    tcpThreads[message[1]].udpServer.resetTimer()


# registry tcp socket is closed
tcpSocket.close()
