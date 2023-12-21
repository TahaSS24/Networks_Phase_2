from pymongo import MongoClient


class DB:
    def __init__(self, db_name="p2p-chat"):
        # Initialize MongoDB Atlas client and select database and collections
        self.atlas_connection_string = "mongodb+srv://Ahmed_Taha:NetworksGroup30@p2p-chat.h8is5dk.mongodb.net/?retryWrites=true&w=majority"
        self.client = MongoClient(self.atlas_connection_string)
        self.db = self.client[db_name]
        self.accounts_collection = self.db["accounts"]
        self.online_peers_collection = self.db["online_peers"]

    def is_account_exist(self, username):
        # Check if an account with the given username exists
        return self.accounts_collection.count_documents({"username": username}) > 0

    def register(self, username, password):
        # Register a new user account
        account = {"username": username, "password": password}
        self.accounts_collection.insert_one(account)

    def get_password(self, username):
        # Retrieve the password for a given username
        user = self.accounts_collection.find_one({"username": username})
        if user:
            return user["password"]
        else:
            return None

    def is_account_online(self, username):
        # Check if an account with the username is online
        return self.online_peers_collection.count_documents({"username": username}) > 0

    def user_login(self, username, ip, port):
        # Log in the user by adding them to the online peers collection
        online_peer = {"username": username, "ip": ip, "port": port}
        self.online_peers_collection.insert_one(online_peer)

    def user_logout(self, username):
        # Log out the user by removing them from the online peers collection
        self.online_peers_collection.delete_one({"username": username})

    def get_peer_ip_port(self, username):
        # Retrieve the IP address and the port number of the username
        res = self.online_peers_collection.find_one({"username": username})
        if res:
            return (res["ip"], res["port"])
        else:
            return None
