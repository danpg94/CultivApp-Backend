from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv, find_dotenv
import os
load_dotenv(find_dotenv())

password = os.environ.get("MONGODB_PWD")

uri = f"mongodb+srv://danpg94:{password}@cherry-cluster.n0x2vso.mongodb.net/?retryWrites=true&w=majority&appName=Cherry-Cluster"
client = MongoClient(uri, server_api=ServerApi('1'))

# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)

dbs = client.list_database_names()
print(dbs)