from socket import *
import threading
import logging


# main process of the peer
class peerMain:
    # peer initializations
    def __init__(self):
        # registry host, port
        self.registryName = input("Enter IP address of registry: ")
        self.registryPort = 15600

        # connection initialization
        self.tcpClientSocket = socket(AF_INET, SOCK_STREAM)
        self.tcpClientSocket.connect((self.registryName, self.registryPort))
        self.udpClientSocket = socket(AF_INET, SOCK_DGRAM)
        self.registryUDPPort = 15500

        # peer info
        self.loginCredentials = (None, None)
        self.isOnline = False
        self.peerServerPort = None

        # timer for hello
        self.timer = None

        # log file initialization
        logging.basicConfig(filename="peer.log", level=logging.INFO, filemode="w")

        choice = "0"
        # as long as the user is not logged out, asks to select an option in the menu
        while True:
            # menu selection prompt
            choice = input(
                "\nOptions: \n\tCreate account: 1 \n\tLogin: 2 \n\tLogout: 3 \n\tSearch for User: 4 \nChoice: "
            )

            # if choice is 1, creates an account with entered username, password
            if choice == "1":
                if self.isOnline:
                    print(
                        "You are currently logged in as {}. Please log out first.".format(
                            self.loginCredentials[0]
                        )
                    )
                else:
                    while True:
                        username = input("Username: ")
                        if len(username) < 4 or len(username) > 12:
                            print("Username must be 4-12 characters long")
                        else:
                            break

                    while True:
                        password = input("Password: ")
                        if len(username) < 4 or len(username) > 12:
                            print("Password must be 4-12 characters long")
                        else:
                            break

                    self.createAccount(username, password)

            # if choice is 2 and user is not logged in, logs in with entered username, password
            elif choice == "2":
                if self.isOnline:
                    print(
                        "You are currently logged in as {}.".format(
                            self.loginCredentials[0]
                        )
                    )
                else:
                    username = input("Username: ")
                    password = input("Password: ")
                    port = input("Port to receive messages: ")
                    self.login(username, password, port)

            # if choice is 3 user is logged out
            elif choice == "3":
                if self.isOnline:
                    self.logout()
                else:
                    print("You are not currently logged in.")

            # if choice is 4 and user is online, then user is asked for username to search
            elif choice == "4":
                if self.isOnline:
                    username = input("Username to be searched: ")
                    self.searchUser(username)
                else:
                    print("Please login to search for users.")

            else:
                print("Invalid input. Please try again")

    def createAccount(self, username, password):
        message = "register-request\n{}\n{}".format(username, password)
        logging.info(
            "Send to {} : {} -> {}".format(
                self.registryName, self.registryPort, message
            )
        )

        self.tcpClientSocket.send(message.encode())
        response = self.tcpClientSocket.recv(1024).decode()
        logging.info(
            "Received from {} : {} -> {}".format(
                self.registryName, self.registryPort, response
            )
        )

        if response == "register-success":
            print("Account created successfully.")
        elif response == "register-username-exist":
            print("Username already exists.")

    def login(self, username, password, peerServerPort):
        message = "login-request\n{}\n{}\n{}".format(username, password, peerServerPort)

        logging.info(
            "Send to {} : {} -> {}".format(
                self.registryName, self.registryPort, message
            )
        )

        self.tcpClientSocket.send(message.encode())
        response = self.tcpClientSocket.recv(1024).decode()
        logging.info(
            "Received from {} : {} -> {}".format(
                self.registryName, self.registryPort, response
            )
        )

        if response == "login-success":
            print("Logged in successfully.")
            self.isOnline = True
            self.loginCredentials = (username, password)
            self.peerServerPort = peerServerPort
            self.sendHelloMessage()

        elif response == "login-fail":
            print("Wrong username or password.")
        elif response == "login-user-online":
            print("Account is already online.")

    def logout(self):
        self.isOnline = False
        self.loginCredentials = (None, None)
        print("Logged out successfully")
        message = "logout"

        logging.info(
            "Send to {} : {} -> {}".format(
                self.registryName, self.registryPort, message
            )
        )
        self.tcpClientSocket.send(message.encode())
        if self.timer is not None:
            self.timer.cancel()

    def searchUser(self, username):
        message = "search-request\n{}".format(username)
        logging.info(
            "Send to {} : {} -> {}".format(
                self.registryName, self.registryPort, message
            )
        )

        self.tcpClientSocket.send(message.encode())
        response = self.tcpClientSocket.recv(1024).decode().split("\n")
        logging.info(
            "Received from {} : {} -> {}".format(
                self.registryName, self.registryPort, response
            )
        )

        if response[0] == "search-success":
            print("{} is logged in -> {} : ".format(username, response[1], response[2]))

        elif response[0] == "search-not-online":
            print("{} is not online.".format(username))
        elif response[0] == "search-not-found":
            print("{} was not found.".format(username))

    def sendHelloMessage(self):
        message = "hello\n{}".format(self.loginCredentials[0])
        logging.info(
            "Send to {} : {} -> {}".format(
                self.registryName, self.registryUDPPort, message
            )
        )
        self.udpClientSocket.sendto(
            message.encode(), (self.registryName, self.registryUDPPort)
        )
        self.timer = threading.Timer(1, self.sendHelloMessage)
        self.timer.start()


# peer is started
peerMain()
